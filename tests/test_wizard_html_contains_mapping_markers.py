from __future__ import annotations

from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def _write_records(path: Path) -> None:
    record = InvoiceRecord(
        doc_id="doc-2",
        issue_date=date(2026, 2, 10),
        merchant_name="Store B",
        total_amount_gross=20.0,
        currency="CNY",
        confidence=Confidence(overall=0.91),
        source=SourceInfo(file_name="sample2.png", sha256="b" * 64, trace_id="trace-2"),
    )
    path.write_text(record.to_json() + "\n", encoding="utf-8")


def test_wizard_html_contains_mapping_markers(tmp_path: Path) -> None:
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

    html = (out_dir / "wizard.html").read_text(encoding="utf-8")
    assert "transformWhitelist" in html
    assert "sample_records.json" in html
    assert "export_template_update.json" in html
    assert "wizard_refine_report.json" in html
    assert "addColumn" in html
    assert "downloadReport" in html
