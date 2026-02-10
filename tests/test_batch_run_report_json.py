import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_batch_run_report_json(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.png").write_bytes(b"fake-png")
    (input_dir / "b.pdf").write_bytes(b"%PDF-1.4\nfake\n")

    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_dir)])
    assert result.exit_code == 0

    report_path = out_dir / "run_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert "summary" in report
    assert report["summary"]["success"] == 1
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["failed"] == 0
    assert "files" in report and len(report["files"]) == 2

    first = report["files"][0]
    for key in ["file", "status", "error_code", "warnings_count", "trace_id", "retry_key"]:
        assert key in first

