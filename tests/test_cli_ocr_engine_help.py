from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_parse_help_contains_ocr_engine_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["parse", "--help"])
    assert result.exit_code == 0
    assert "--ocr-engine" in result.stdout
    assert "--fixtures-dir" in result.stdout
    assert "fixtures" in result.stdout
