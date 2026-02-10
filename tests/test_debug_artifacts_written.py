import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_parse_debug_artifact_written_and_default_off(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")
    out_dir = tmp_path / "out"

    runner = CliRunner()
    default_result = runner.invoke(app, ["parse", str(sample), "--out", str(out_dir)])
    assert default_result.exit_code == 0
    assert not list(out_dir.glob("debug_*.json"))

    debug_result = runner.invoke(app, ["parse", str(sample), "--debug-artifacts", "--out", str(out_dir)])
    assert debug_result.exit_code == 0
    debug_files = list(out_dir.glob("debug_*.json"))
    assert debug_files

    payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert "normalized_lines" in payload["rules"]
    assert "candidates" in payload["rules"]
    assert "selected" in payload["rules"]


def test_batch_debug_artifact_written(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.png").write_bytes(b"fake")
    out_dir = tmp_path / "out"

    runner = CliRunner()
    result = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_dir), "--debug-artifacts"])
    assert result.exit_code == 0

    debug_files = list(out_dir.glob("debug_*.json"))
    assert debug_files
    payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
    assert payload["status"] in {"success", "skipped", "failed"}
    assert "rules" in payload

