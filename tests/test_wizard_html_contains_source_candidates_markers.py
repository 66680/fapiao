from __future__ import annotations

from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo


def _write_records(path: Path) -> None:
    record = InvoiceRecord(
        doc_id="doc-3",
        issue_date=date(2026, 2, 11),
        merchant_name="Store C",
        total_amount_gross=32.5,
        currency="CNY",
        confidence=Confidence(overall=0.95),
        source=SourceInfo(file_name="sample3.png", sha256="c" * 64, trace_id="trace-3"),
    )
    path.write_text(record.to_json() + "\n", encoding="utf-8")


def test_wizard_html_contains_source_candidates_markers(tmp_path: Path) -> None:
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
    assert "sourceCandidatesList" in html
    assert "addCandidateBtn" in html
    assert "source_candidates" in html
