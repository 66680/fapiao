import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from invstruct.cli import app


def test_export_warnings_columns(tmp_path: Path) -> None:
    records_path = tmp_path / "records.jsonl"
    record = {
        "doc_id": "doc-1",
        "doc_type": "receipt",
        "merchant_name": "Store A",
        "issue_date": "2026-02-09",
        "total_amount_gross": 88.2,
        "currency": "CNY",
        "status": "success",
        "warnings": [{"page_index": 2, "reason": "no_text"}],
        "retry_key": "abcd:1:1",
        "parser_version": "pdfplumber@0.11.9",
        "source": {"file_name": "a.pdf", "trace_id": "trace-1", "sha256": "a" * 64},
    }
    records_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    out_csv = tmp_path / "out.csv"
    out_xlsx = tmp_path / "out.xlsx"
    runner = CliRunner()
    result = runner.invoke(app, ["export", str(records_path), "--csv", str(out_csv), "--xlsx", str(out_xlsx)])
    assert result.exit_code == 0

    frame = pd.read_csv(out_csv, comment="#")
    for col in ["warnings_count", "warnings_json", "parser_version", "retry_key"]:
        assert col in frame.columns
    assert int(frame["warnings_count"].max()) == 1
    assert frame["warnings_json"].astype(str).str.contains("no_text").any()
