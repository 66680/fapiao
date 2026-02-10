from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from invstruct.cli import app


def _write(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_diff_markdown_contains_tables(tmp_path: Path) -> None:
    a_path = tmp_path / "a.yaml"
    b_path = tmp_path / "b.yaml"
    out_dir = tmp_path / "out_diff"

    _write(
        a_path,
        {
            "template_id": "a",
            "columns": [{"name": "merchant", "source": "merchant_name", "transform": "as_is"}],
        },
    )
    _write(
        b_path,
        {
            "template_id": "b",
            "columns": [
                {"name": "merchant", "source": "source.file_name", "transform": "as_is"},
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
            str(a_path),
            "--b",
            str(b_path),
            "--out",
            str(out_dir),
            "--format",
            "md",
        ],
    )
    assert result.exit_code == 0, result.stdout
    md_text = (out_dir / "diff_report.md").read_text(encoding="utf-8")
    assert "| Added | Removed | Modified | Moved |" in md_text
    assert "| Column | Index |" in md_text
    assert "| Name A | Index A | Name B | Index B | Changed Fields |" in md_text
