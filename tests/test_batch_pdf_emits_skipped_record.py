import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_batch_pdf_emits_skipped_record(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "invoice.pdf").write_bytes(b"%PDF-1.4\nfake\n")

    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_dir)])
    assert result.exit_code == 0

    records_path = out_dir / "records.jsonl"
    lines = records_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["status"] == "skipped"
    assert record["error_code"] == "E3001"
    assert record["error_message"] == "PDF not supported yet"
    assert record["source"]["trace_id"]
    assert len(record["source"]["sha256"]) == 64

