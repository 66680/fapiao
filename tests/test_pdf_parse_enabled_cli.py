import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invstruct.cli import app
from pdf_test_utils import write_text_pdf

pdfplumber = pytest.importorskip("pdfplumber")

def test_pdf_parse_enabled_cli(tmp_path: Path) -> None:
    sample_pdf = tmp_path / "sample.pdf"
    write_text_pdf(
        sample_pdf,
        pages=[["My Store LLC", "Invoice No INV123", "Date 2026-02-09", "Total Amount 123.45"]],
    )

    runner = CliRunner()
    result = runner.invoke(app, ["parse", str(sample_pdf), "--allow-pdf"])
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["source"]["trace_id"]
    assert len(payload["source"]["sha256"]) == 64
    assert payload["retry_key"]
    assert str(payload["parser_version"]).startswith("pdfplumber@")
    assert payload["total_amount_gross"] is not None
    assert payload["provenance"]["total_amount_gross"]["page"] == 1
