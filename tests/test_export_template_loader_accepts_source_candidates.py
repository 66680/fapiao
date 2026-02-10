from __future__ import annotations

from pathlib import Path

import yaml

from invstruct.export_templates.loader import load_export_template


def test_export_template_loader_accepts_source_candidates(tmp_path: Path) -> None:
    template_path = tmp_path / "candidate_template.yaml"
    template_path.write_text(
        yaml.safe_dump(
            {
                "template_id": "candidate_tpl",
                "version": "1.0.0",
                "columns": [
                    {
                        "name": "merchant",
                        "source_candidates": ["merchant_name", "source.file_name"],
                        "transform": "as_is",
                    }
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    template = load_export_template(template_path)
    assert template.template_id == "candidate_tpl"
    assert template.columns[0].source_candidates == ["merchant_name", "source.file_name"]
