import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_parse_pdf_still_errors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        pdf_path = Path("sample.pdf")
        pdf_path.write_bytes(b"%PDF-1.4\nfake\n")
        result = runner.invoke(app, ["parse", str(pdf_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "E3001"

