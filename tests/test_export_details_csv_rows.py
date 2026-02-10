from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from invstruct.exporters.details_csv import DETAIL_FIELDS, write_details_csv
from invstruct.schemas import Confidence, FieldProvenance, InvoiceRecord, SourceInfo


def test_export_details_csv_rows(tmp_path: Path) -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        doc_type="receipt",
        issue_date=date(2026, 2, 9),
        merchant_name="Store A",
        currency="CNY",
        total_amount_gross=12.5,
        confidence=Confidence(overall=0.92, fields={"merchant_name": 0.95}),
        provenance={
            "merchant_name": FieldProvenance(
                page=1,
                bbox=[1.0, 2.0, 3.0, 4.0],
                extractor="rules.merchant",
                line_id=0,
                line_text="Store A",
            )
        },
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    output = tmp_path / "details.csv"
    write_details_csv([record], output)

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == len(DETAIL_FIELDS)
    merchant_rows = [row for row in rows if row["field_name"] == "merchant_name"]
    assert merchant_rows
    assert merchant_rows[0]["extractor"] == "rules.merchant"
    issue_date_rows = [row for row in rows if row["field_name"] == "issue_date"]
    assert issue_date_rows[0]["field_value"] == "2026-02-09"
