import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from invstruct.cli import app


def test_export_generates_csv_and_excel(tmp_path: Path) -> None:
    records = tmp_path / "records.jsonl"
    payload = {
        "merchant_name": "My Store",
        "issue_date": "2026-02-09",
        "total_amount_gross": 12.34,
        "currency": "CNY",
        "invoice_number": "INV001",
        "merchant_tax_id": "91350100MA12345678",
        "source": {"trace_id": "t1", "sha256": "abc"},
    }
    records.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    out_csv = tmp_path / "out.csv"
    out_xlsx = tmp_path / "out.xlsx"

    runner = CliRunner()
    result = runner.invoke(app, ["export", str(records), "--csv", str(out_csv), "--xlsx", str(out_xlsx)])
    assert result.exit_code == 0
    assert out_csv.exists()
    assert out_xlsx.exists()

    frame = pd.read_csv(out_csv, comment="#")
    for col in ["merchant", "issue_date", "total_amount_gross", "currency", "invoice_no", "tax_id", "trace_id", "sha256"]:
        assert col in frame.columns
