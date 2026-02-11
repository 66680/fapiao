import click
from typer.testing import CliRunner
from typer.main import get_command

from invstruct.cli import app


def test_cli_parse_help_contains_ocr_engine_options() -> None:
    click_app = get_command(app)
    parse_cmd = click_app.commands["parse"]
    option_flags: set[str] = set()
    for param in parse_cmd.params:
        if isinstance(param, click.Option):
            option_flags.update(param.opts)

    assert "--ocr-engine" in option_flags
    assert "--fixtures-dir" in option_flags

    runner = CliRunner()
    result = runner.invoke(app, ["parse", "--help"])
    assert result.exit_code == 0
