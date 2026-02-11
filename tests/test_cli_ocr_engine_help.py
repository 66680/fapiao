from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_parse_help_contains_ocr_engine_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parse", "--help"])
    assert result.exit_code == 0
    cleaned = result.stdout.replace("\u001b", " ")
    assert "ocr-engine" in cleaned
    assert "fixtures-dir" in cleaned
    assert "fixtures" in cleaned
