import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_batch_skips_pdf_with_e3001_and_continues(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.png").write_bytes(b"png")
    (input_dir / "b.pdf").write_bytes(b"%PDF-1.4")

    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_dir)])
    assert result.exit_code == 0

    failures = (out_dir / "failures.jsonl").read_text(encoding="utf-8").splitlines()
    assert failures
    parsed = json.loads(failures[0])
    assert parsed["error"]["code"] == "E3001"

