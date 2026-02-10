from __future__ import annotations

import json

from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_export_entrypoints_compat() -> None:
    runner = CliRunner()

    result_list = runner.invoke(app, ["export", "list"])
    assert result_list.exit_code == 0, result_list.stdout
    payload_list = json.loads(result_list.stdout)
    assert "templates" in payload_list

    result_templates = runner.invoke(app, ["export", "templates", "list"])
    assert result_templates.exit_code == 0, result_templates.stdout
    payload_templates = json.loads(result_templates.stdout)
    assert "templates" in payload_templates
