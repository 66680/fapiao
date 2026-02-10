from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from invstruct.export_templates.models import ExportTemplateSpec
from invstruct.exporters.mapped_csv import write_mapped_csv
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_mapped_csv_uses_source_candidates_fallback(tmp_path: Path) -> None:
    template = ExportTemplateSpec.model_validate(
        {
            "template_id": "fallback_tpl",
            "columns": [
                {
                    "name": "merchant",
                    "source": "merchant_name",
                    "source_candidates": ["merchant_name", "source.file_name"],
                    "transform": "as_is",
                },
                {
                    "name": "amount",
                    "source": "total_amount_gross",
                    "source_candidates": ["total_amount_gross", "subtotal_amount_net"],
                    "transform": "amount_2dp",
                    "default": "0.00",
                },
            ],
        }
    )

    record = InvoiceRecord(
        doc_id="doc-1",
        issue_date=date(2026, 2, 9),
        merchant_name=None,
        total_amount_gross=0.0,
        subtotal_amount_net=25.0,
        currency="CNY",
        confidence=Confidence(overall=0.9),
        source=SourceInfo(file_name="fallback_source.png", sha256="a" * 64, trace_id="t1"),
    )
    out_path = tmp_path / "out.csv"
    write_mapped_csv([record], out_path, template)

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        row = next(reader)

    assert row["merchant"] == "fallback_source.png"
    assert row["amount"] == "0.00"
