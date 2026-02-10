from __future__ import annotations

from invstruct.anomalies.engine import attach_anomalies
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def _make_record(doc_id: str, trace_id: str, sha: str) -> InvoiceRecord:
    return InvoiceRecord(
        doc_id=doc_id,
        merchant_name="Store A",
        issue_date="2026-02-09",
        total_amount_gross=20.0,
        invoice_number="INV-001",
        merchant_tax_id="91350100MA12345678",
        confidence=Confidence(overall=0.95),
        source=SourceInfo(file_name=f"{doc_id}.png", sha256=sha, trace_id=trace_id),
    )


def test_anomaly_duplicate_by_sha256() -> None:
    records = [
        _make_record("doc-1", "trace-1", "a" * 64),
        _make_record("doc-2", "trace-2", "a" * 64),
    ]
    result = attach_anomalies(records)
    for record in result:
        codes = {item.code for item in record.anomalies}
        assert "DUPLICATE_SHA256" in codes
