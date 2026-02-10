import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_parse_outputs_json(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")

    runner = CliRunner()
    result = runner.invoke(app, ["parse", str(sample)])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["source"]["trace_id"]
    assert payload["source"]["sha256"]

