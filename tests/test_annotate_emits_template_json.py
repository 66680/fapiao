from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_annotate_emits_template_json(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")
    out_dir = tmp_path / "anno"

    runner = CliRunner()
    result = runner.invoke(app, ["template", "annotate", "--from", str(sample), "--out", str(out_dir)])
    assert result.exit_code == 0, result.stdout

    blocks_path = out_dir / "blocks.json"
    pages_path = out_dir / "pages.json"
    template_path = out_dir / "template.json"
    editor_path = out_dir / "editor.html"

    assert blocks_path.exists()
    assert pages_path.exists()
    assert template_path.exists()
    assert editor_path.exists()

    blocks_payload = json.loads(blocks_path.read_text(encoding="utf-8"))
    assert blocks_payload["blocks"]
    assert "bbox_norm" in blocks_payload["blocks"][0]

    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    assert template_payload["template_id"]
