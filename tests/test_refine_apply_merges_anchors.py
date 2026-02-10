from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from invstruct.cli import app
from invstruct.templates.loader import load_template


def test_refine_apply_merges_anchors(tmp_path: Path) -> None:
    base_yaml = tmp_path / "base.yaml"
    base_yaml.write_text(
        yaml.safe_dump(
            {
                "template_id": "base_receipt",
                "version": "1.0.0",
                "locale": "zh-CN",
                "doc_type": "receipt",
                "aliases": {"issue_date": ["日期"]},
                "anchors": {
                    "issue_date": {
                        "keywords": ["日期"],
                        "roi": [0.0, 0.0, 1.0, 1.0],
                        "direction": "right_or_below",
                    }
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    update_json = tmp_path / "template_update.json"
    update_json.write_text(
        json.dumps(
            {
                "anchors": {
                    "issue_date": {
                        "keywords": ["开票日期", "Date"],
                        "roi": [0.1, 0.1, 0.6, 0.3],
                        "direction": "right",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    out_yaml = tmp_path / "merged.yaml"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "template",
            "refine",
            "apply",
            "--base",
            str(base_yaml),
            "--update",
            str(update_json),
            "--out",
            str(out_yaml),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out_yaml.exists()

    merged = load_template(out_yaml)
    assert merged.anchors["issue_date"].direction == "right"
    assert merged.anchors["issue_date"].roi == [0.1, 0.1, 0.6, 0.3]
    assert merged.anchors["issue_date"].keywords == ["开票日期", "Date"]
