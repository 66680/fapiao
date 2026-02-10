from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_editor_html_contains_live_roi_markers(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")
    out_dir = tmp_path / "anno"

    runner = CliRunner()
    result = runner.invoke(app, ["template", "annotate", "--from", str(sample), "--out", str(out_dir)])
    assert result.exit_code == 0, result.stdout

    editor_path = out_dir / "editor.html"
    assert editor_path.exists()
    html = editor_path.read_text(encoding="utf-8")

    assert 'id="dragRect"' in html
    assert 'id="coordHUD"' in html
    assert "pointerdown" in html
    assert "Escape" in html
    assert "shiftKey" in html
