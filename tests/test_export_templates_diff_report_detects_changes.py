from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from invstruct.cli import app


def _write_template(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_export_templates_diff_report_detects_changes(tmp_path: Path) -> None:
    template_a = tmp_path / "a.yaml"
    template_b = tmp_path / "b.yaml"
    out_dir = tmp_path / "diff"

    _write_template(
        template_a,
        {
            "template_id": "tpl_a",
            "columns": [
                {"name": "date", "source": "issue_date", "transform": "date_iso"},
                {"name": "merchant", "source": "merchant_name", "transform": "as_is"},
            ],
        },
    )
    _write_template(
        template_b,
        {
            "template_id": "tpl_b",
            "columns": [
                {"name": "merchant", "source": "source.file_name", "transform": "as_is"},
                {"name": "date", "source_candidates": ["issue_date", "source.trace_id"], "transform": "date_iso"},
                {"name": "amount", "source": "total_amount_gross", "transform": "amount_2dp"},
            ],
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "templates",
            "diff",
            "--a",
            str(template_a),
            "--b",
            str(template_b),
            "--out",
            str(out_dir),
            "--format",
            "json,md",
        ],
    )
    assert result.exit_code == 0, result.stdout

    json_path = out_dir / "diff_report.json"
    md_path = out_dir / "diff_report.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["added"] >= 1
    assert payload["summary"]["modified"] >= 1
    assert payload["summary"]["moved"] >= 1
