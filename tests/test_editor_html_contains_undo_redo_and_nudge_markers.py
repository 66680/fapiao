from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_editor_html_contains_undo_redo_and_nudge_markers(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")
    out_dir = tmp_path / "anno"

    runner = CliRunner()
    result = runner.invoke(app, ["template", "annotate", "--from", str(sample), "--out", str(out_dir)])
    assert result.exit_code == 0, result.stdout

    html = (out_dir / "editor.html").read_text(encoding="utf-8")
    assert "historyStack" in html
    assert "undo" in html
    assert "redo" in html
    assert "ArrowLeft" in html
    assert "ctrlKey" in html
    assert "shiftKey" in html
