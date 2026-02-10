from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_invoice_record_roundtrip() -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        doc_type="receipt",
        total_amount_gross=100.5,
        confidence=Confidence(overall=0.91, fields={"total_amount_gross": 0.95}),
        source=SourceInfo(file_name="a.jpg", sha256="a" * 64, trace_id="t-1"),
    )

    dumped = record.to_json()
    loaded = InvoiceRecord.from_json(dumped)

    assert loaded.doc_id == "doc-1"
    assert loaded.total_amount_gross == 100.5
    assert loaded.confidence.fields["total_amount_gross"] == 0.95

