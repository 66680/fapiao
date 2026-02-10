from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def _write_records(path: Path) -> None:
    record = InvoiceRecord(
        doc_id="doc-1",
        issue_date=date(2026, 2, 9),
        merchant_name="Store A",
        total_amount_gross=18.5,
        currency="CNY",
        confidence=Confidence(overall=0.88),
        source=SourceInfo(file_name="sample.png", sha256="a" * 64, trace_id="trace-1"),
    )
    path.write_text(record.to_json() + "\n", encoding="utf-8")


def test_export_wizard_emits_required_files(tmp_path: Path) -> None:
    records = tmp_path / "records.jsonl"
    out_dir = tmp_path / "wizard"
    _write_records(records)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "templates",
            "wizard",
            "--in",
            str(records),
            "--base",
            "generic_expense_v1",
            "--out",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0, result.stdout

    required_files = [
        "export_template.json",
        "sample_records.json",
        "field_catalog.json",
        "wizard.html",
        "wizard_report.json",
    ]
    for name in required_files:
        assert (out_dir / name).exists(), name

    template_payload = json.loads((out_dir / "export_template.json").read_text(encoding="utf-8"))
    assert template_payload["template_id"] == "generic_expense_v1"

    sample_payload = json.loads((out_dir / "sample_records.json").read_text(encoding="utf-8"))
    assert sample_payload["rows"][0]["doc_id"] == "doc-1"
