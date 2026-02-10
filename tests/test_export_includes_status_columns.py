import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from invstruct.cli import app


def test_export_includes_status_columns(tmp_path: Path) -> None:
    records_path = tmp_path / "records.jsonl"
    success = {
        "merchant_name": "Store A",
        "issue_date": "2026-02-09",
        "total_amount_gross": 10.2,
        "currency": "CNY",
        "invoice_number": "INV-1",
        "merchant_tax_id": "TAX-1",
        "status": "success",
        "source": {"trace_id": "trace-success", "sha256": "a" * 64},
    }
    skipped = {
        "merchant_name": None,
        "issue_date": None,
        "total_amount_gross": None,
        "currency": "CNY",
        "invoice_number": None,
        "merchant_tax_id": None,
        "status": "skipped",
        "error_code": "E3001",
        "error_message": "PDF not supported yet",
        "source": {"trace_id": "trace-skipped", "sha256": "b" * 64},
    }
    records_path.write_text(
        json.dumps(success, ensure_ascii=False) + "\n" + json.dumps(skipped, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    out_csv = tmp_path / "out.csv"
    out_xlsx = tmp_path / "out.xlsx"
    runner = CliRunner()
    result = runner.invoke(app, ["export", str(records_path), "--csv", str(out_csv), "--xlsx", str(out_xlsx)])
    assert result.exit_code == 0

    frame = pd.read_csv(out_csv, comment="#")
    for col in ["status", "error_code", "error_message"]:
        assert col in frame.columns

    skipped_rows = frame[frame["status"] == "skipped"]
    assert not skipped_rows.empty
    assert skipped_rows.iloc[0]["error_code"] == "E3001"
    assert skipped_rows.iloc[0]["error_message"] == "PDF not supported yet"
