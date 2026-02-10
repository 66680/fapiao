from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from invstruct.export_templates.models import ExportTemplateSpec
from invstruct.exporters.mapped_csv import write_mapped_csv
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def test_candidate_strategy_prefer_primary(tmp_path: Path) -> None:
    template = ExportTemplateSpec.model_validate(
        {
            "template_id": "strategy_tpl",
            "columns": [
                {
                    "name": "merchant_first_non_empty",
                    "source": "merchant_name",
                    "source_candidates": ["source.file_name", "merchant_name"],
                    "candidate_strategy": "first_non_empty",
                    "transform": "as_is",
                },
                {
                    "name": "merchant_prefer_primary",
                    "source": "merchant_name",
                    "source_candidates": ["source.file_name", "merchant_name"],
                    "candidate_strategy": "prefer_primary_source",
                    "transform": "as_is",
                },
            ],
        }
    )
    record = InvoiceRecord(
        doc_id="doc-1",
        issue_date=date(2026, 2, 9),
        merchant_name="Real Merchant",
        total_amount_gross=10.0,
        currency="CNY",
        confidence=Confidence(overall=0.9),
        source=SourceInfo(file_name="fallback_name.png", sha256="a" * 64, trace_id="t-1"),
    )
    out_path = tmp_path / "out.csv"
    write_mapped_csv([record], out_path, template)

    with out_path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))

    assert row["merchant_first_non_empty"] == "fallback_name.png"
    assert row["merchant_prefer_primary"] == "Real Merchant"
