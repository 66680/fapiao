from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from invstruct.anomalies.models import Anomaly
from invstruct.config import AnomalyConfig
from invstruct.schemas import InvoiceRecord
from invstruct.templates.models import TemplateAnomalyOverrides, TemplateSpec

CORE_FIELDS = ("merchant_name", "issue_date", "total_amount_gross")


def _append(record: InvoiceRecord, anomaly: Anomaly) -> None:
    if any(item.code == anomaly.code and item.details == anomaly.details for item in record.anomalies):
        return
    record.anomalies.append(anomaly)


def _get_record_value(record: InvoiceRecord, field_name: str) -> str:
    value = getattr(record, field_name, None)
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value).strip()


def merge_anomaly_config(base: AnomalyConfig, override: TemplateAnomalyOverrides | dict | None) -> AnomalyConfig:
    if override is None:
        return base.model_copy(deep=True)

    override_obj = override
    if isinstance(override, dict):
        override_obj = TemplateAnomalyOverrides.model_validate(override)

    merged = base.model_copy(deep=True)
    if override_obj.duplicate is not None:
        merged = merged.model_copy(
            update={"duplicate": merged.duplicate.model_copy(update=override_obj.duplicate.model_dump(exclude_none=True))}
        )
    if override_obj.amount_mismatch is not None:
        merged = merged.model_copy(
            update={
                "amount_mismatch": merged.amount_mismatch.model_copy(
                    update=override_obj.amount_mismatch.model_dump(exclude_none=True)
                )
            }
        )
    if override_obj.low_conf is not None:
        merged = merged.model_copy(
            update={"low_conf": merged.low_conf.model_copy(update=override_obj.low_conf.model_dump(exclude_none=True))}
        )
    return merged


def _detect_low_conf_or_missing(record: InvoiceRecord, config) -> None:
    if not config.enabled:
        return
    if record.confidence.overall < config.threshold:
        _append(
            record,
            Anomaly(
                code="LOW_CONFIDENCE",
                message="Confidence below threshold",
                severity="warning",
                details={"overall": record.confidence.overall, "threshold": config.threshold},
            ),
        )

    if not config.require_core_fields:
        return
    missing = [field for field in CORE_FIELDS if getattr(record, field) in (None, "")]
    if missing:
        _append(
            record,
            Anomaly(
                code="MISSING_CORE_FIELDS",
                message="Core fields missing",
                severity=config.missing_severity,
                details={"fields": missing},
            ),
        )


def _detect_amount_mismatch(record: InvoiceRecord, config) -> None:
    if not config.enabled:
        return
    if (
        record.subtotal_amount_net is None
        or record.tax_amount is None
        or record.total_amount_gross is None
    ):
        return
    expected = round(float(record.subtotal_amount_net) + float(record.tax_amount), 2)
    actual = round(float(record.total_amount_gross), 2)
    if abs(expected - actual) > float(config.tolerance):
        _append(
            record,
            Anomaly(
                code="AMOUNT_MISMATCH",
                message="Gross amount does not equal subtotal + tax",
                severity="critical",
                details={
                    "expected_total": expected,
                    "actual_total": actual,
                    "delta": round(actual - expected, 2),
                    "tolerance": float(config.tolerance),
                },
            ),
        )


def attach_anomalies(
    records: Iterable[InvoiceRecord],
    low_conf_threshold: float | None = None,
    config: AnomalyConfig | None = None,
    templates: dict[str, TemplateSpec] | None = None,
) -> list[InvoiceRecord]:
    base_config = config.model_copy(deep=True) if config is not None else AnomalyConfig()
    if low_conf_threshold is not None:
        base_config = base_config.model_copy(
            update={"low_conf": base_config.low_conf.model_copy(update={"threshold": low_conf_threshold})}
        )

    rows = list(records)
    effective_configs: list[AnomalyConfig] = []

    for record in rows:
        record.anomalies = list(record.anomalies or [])
        template_override = None
        if templates is not None and record.template_id:
            template_spec = templates.get(record.template_id)
            if template_spec is not None:
                template_override = template_spec.anomalies
        effective = merge_anomaly_config(base_config, template_override)
        effective_configs.append(effective)
        _detect_low_conf_or_missing(record, effective.low_conf)
        _detect_amount_mismatch(record, effective.amount_mismatch)

    by_sha: dict[str, list[int]] = defaultdict(list)
    for idx, record in enumerate(rows):
        sha = str(record.source.sha256 or "").strip()
        if sha:
            by_sha[sha].append(idx)

    for sha, indices in by_sha.items():
        if len(indices) < 2:
            continue
        for idx in indices:
            duplicate_cfg = effective_configs[idx].duplicate
            if not (duplicate_cfg.enabled and duplicate_cfg.use_sha256):
                continue
            _append(
                rows[idx],
                Anomaly(
                    code="DUPLICATE_SHA256",
                    message="Duplicate source hash",
                    severity="critical",
                    details={"sha256": sha, "count": len(indices)},
                ),
            )

    business_groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[int]] = defaultdict(list)
    for idx, record in enumerate(rows):
        duplicate_cfg = effective_configs[idx].duplicate
        if not (duplicate_cfg.enabled and duplicate_cfg.use_business_key):
            continue
        fields = tuple(duplicate_cfg.business_key_fields)
        values = tuple(_get_record_value(record, field_name) for field_name in fields)
        if any(values):
            business_groups[(fields, values)].append(idx)

    for (fields, values), indices in business_groups.items():
        if len(indices) < 2:
            continue
        field_map = {field_name: values[pos] for pos, field_name in enumerate(fields)}
        for idx in indices:
            duplicate_cfg = effective_configs[idx].duplicate
            if not (duplicate_cfg.enabled and duplicate_cfg.use_business_key):
                continue
            _append(
                rows[idx],
                Anomaly(
                    code="DUPLICATE_BUSINESS_KEY",
                    message="Duplicate invoice business key",
                    severity="warning",
                    details={"fields": field_map, "count": len(indices)},
                ),
            )

    return rows
