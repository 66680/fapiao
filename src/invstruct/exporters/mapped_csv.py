from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from invstruct.export_templates.models import ExportColumnSpec, ExportTemplateSpec
from invstruct.schemas import InvoiceRecord


def _resolve_value(payload: dict[str, Any], source: str) -> Any:
    cursor: Any = payload
    for part in source.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(part)
        else:
            return None
    return cursor


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _candidate_sources(column: ExportColumnSpec) -> list[str]:
    configured = [item for item in (column.source_candidates or []) if isinstance(item, str) and item.strip()]
    if not configured and column.source:
        return [column.source]

    strategy = column.candidate_strategy
    if strategy == "prefer_primary_source" and column.source:
        primary = column.source.strip()
        rest = [item for item in configured if item != primary]
        return [primary, *rest]
    return configured


def resolve_source_value(payload: dict[str, Any], column: ExportColumnSpec) -> tuple[Any, str | None, int | None]:
    candidates = _candidate_sources(column)

    for index, source in enumerate(candidates):
        raw_value = _resolve_value(payload, source)
        if not _is_missing_value(raw_value):
            return raw_value, source, index
    return None, None, None


def _as_is(value: Any) -> Any:
    return value


def _date_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)


def _amount_2dp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return None


def _anomaly_codes_join(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        codes: list[str] = []
        for item in value:
            if isinstance(item, dict):
                code = item.get("code")
                if code:
                    codes.append(str(code))
            else:
                code = getattr(item, "code", None)
                if code:
                    codes.append(str(code))
        return "|".join(codes)
    return ""


TRANSFORMS = {
    "as_is": _as_is,
    "date_iso": _date_iso,
    "amount_2dp": _amount_2dp,
    "anomaly_codes_join": _anomaly_codes_join,
}


def write_mapped_csv(records: list[InvoiceRecord], out_path: Path, export_template: ExportTemplateSpec) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    columns = export_template.columns
    headers = [column.name for column in columns]

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for record in records:
            payload = record.to_dict()
            row: dict[str, Any] = {}
            for column in columns:
                raw_value, _, _ = resolve_source_value(payload, column)
                transform = TRANSFORMS[column.transform]
                value = transform(raw_value)
                row[column.name] = column.default if _is_missing_value(value) else value
            writer.writerow(row)
