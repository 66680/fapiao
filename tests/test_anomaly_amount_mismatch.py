from __future__ import annotations

from datetime import date

from invstruct.anomalies.engine import attach_anomalies
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_anomaly_amount_mismatch() -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        merchant_name="Store A",
        issue_date=date(2026, 2, 9),
        total_amount_gross=20.0,
        subtotal_amount_net=10.0,
        tax_amount=1.0,
        confidence=Confidence(overall=0.9),
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    result = attach_anomalies([record])[0]
    codes = {item.code for item in result.anomalies}
    assert "AMOUNT_MISMATCH" in codes
