from __future__ import annotations

import json

from typer.testing import CliRunner

from invstruct.cli import app


def test_cli_export_templates_list() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["export", "templates", "list"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    template_ids = {item["template_id"] for item in payload["templates"]}
    assert "generic_expense_v1" in template_ids
