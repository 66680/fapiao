from __future__ import annotations

from datetime import date

from invstruct.anomalies.engine import attach_anomalies
from invstruct.config import AmountMismatchConfig, AnomalyConfig
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_amount_mismatch_tolerance_override() -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        merchant_name="Store A",
        issue_date=date(2026, 2, 9),
        total_amount_gross=11.03,
        subtotal_amount_net=10.0,
        tax_amount=1.0,
        confidence=Confidence(overall=0.95),
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    config = AnomalyConfig(amount_mismatch=AmountMismatchConfig(enabled=True, tolerance=0.05))
    result = attach_anomalies([record], config=config)[0]
    codes = {item.code for item in result.anomalies}
    assert "AMOUNT_MISMATCH" not in codes
