from __future__ import annotations

from datetime import date

from invstruct.anomalies.engine import attach_anomalies
from invstruct.config import AnomalyConfig
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo
from invstruct.templates.models import TemplateAnomalyOverrides, TemplateDuplicateOverride, TemplateSpec


def _make_record(doc_id: str, trace_id: str) -> InvoiceRecord:
    return InvoiceRecord(
        doc_id=doc_id,
        template_id="tpl_no_dup",
        merchant_name="Store A",
        issue_date=date(2026, 2, 9),
        total_amount_gross=20.0,
        invoice_number="INV-001",
        merchant_tax_id="91350100MA12345678",
        confidence=Confidence(overall=0.95),
        source=SourceInfo(file_name=f"{doc_id}.png", sha256="a" * 64, trace_id=trace_id),
    )


def test_template_anomaly_override_disables_duplicate() -> None:
    records = [_make_record("doc-1", "trace-1"), _make_record("doc-2", "trace-2")]
    template = TemplateSpec(
        template_id="tpl_no_dup",
        anomalies=TemplateAnomalyOverrides(duplicate=TemplateDuplicateOverride(enabled=False)),
    )
    result = attach_anomalies(records, config=AnomalyConfig(), templates={"tpl_no_dup": template})
    for item in result:
        codes = {anomaly.code for anomaly in item.anomalies}
        assert "DUPLICATE_SHA256" not in codes
        assert "DUPLICATE_BUSINESS_KEY" not in codes
