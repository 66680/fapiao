from __future__ import annotations

from invstruct.anomalies.engine import attach_anomalies
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_anomaly_low_conf_missing_core() -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        merchant_name=None,
        issue_date=None,
        total_amount_gross=None,
        confidence=Confidence(overall=0.2),
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    result = attach_anomalies([record], low_conf_threshold=0.75)[0]
    codes = {item.code for item in result.anomalies}
    assert "LOW_CONFIDENCE" in codes
    assert "MISSING_CORE_FIELDS" in codes
