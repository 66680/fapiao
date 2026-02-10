import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from invstruct.cli import app
from pdf_test_utils import write_text_pdf

pdfplumber = pytest.importorskip("pdfplumber")


def test_pdf_parse_batch_upgrade(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.png").write_bytes(b"fake-png")
    write_text_pdf(
        input_dir / "b.pdf",
        pages=[["My Store LLC", "Invoice No INV998", "Date 2026-02-09", "Total Amount 88.30"]],
    )

    runner = CliRunner()

    out_default = tmp_path / "out_default"
    result_default = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_default)])
    assert result_default.exit_code == 0
    default_records = [
        json.loads(line)
        for line in (out_default / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(default_records) == 2
    pdf_default = next(item for item in default_records if item["source"]["file_name"] == "b.pdf")
    assert pdf_default["status"] == "skipped"

    out_enabled = tmp_path / "out_enabled"
    result_enabled = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_enabled), "--allow-pdf"])
    assert result_enabled.exit_code == 0
    enabled_records = [
        json.loads(line)
        for line in (out_enabled / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(enabled_records) == 2
    pdf_enabled = next(item for item in enabled_records if item["source"]["file_name"] == "b.pdf")
    assert pdf_enabled["status"] == "success"

    out_csv = tmp_path / "out.csv"
    out_xlsx = tmp_path / "out.xlsx"
    export_result = runner.invoke(app, ["export", str(out_enabled / "records.jsonl"), "--csv", str(out_csv), "--xlsx", str(out_xlsx)])
    assert export_result.exit_code == 0
    frame = pd.read_csv(out_csv, comment="#")
    assert len(frame) == 2
