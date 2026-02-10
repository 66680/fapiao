from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from invstruct.anomalies.models import Anomaly
from invstruct.export_templates.loader import get_export_template
from invstruct.exporters.mapped_csv import write_mapped_csv
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_mapped_csv_export_columns_order(tmp_path: Path) -> None:
    template = get_export_template("generic_expense_minimal_v1", "configs/export_templates")
    assert template is not None

    record = InvoiceRecord(
        doc_id="doc-1",
        issue_date=date(2026, 2, 9),
        merchant_name="Store A",
        total_amount_gross=12.3,
        currency="CNY",
        anomalies=[Anomaly(code="LOW_CONFIDENCE", message="low")],
        confidence=Confidence(overall=0.9),
        source=SourceInfo(file_name="a.png", sha256="a" * 64, trace_id="t-1"),
    )
    output = tmp_path / "mapped.csv"
    write_mapped_csv([record], output, template)

    with output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        row = next(reader)

    assert header == [column.name for column in template.columns]
    assert row[0] == "2026-02-09"
    assert row[2] == "12.30"
    assert row[-1] == "LOW_CONFIDENCE"
