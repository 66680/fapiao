from pathlib import Path
import subprocess
import sys

from invstruct.templates.loader import load_template


def test_template_init_generates_valid_yaml(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")
    out_template = tmp_path / "generated.yaml"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "invstruct.cli",
            "template",
            "init",
            "--from",
            str(sample),
            "--out",
            str(out_template),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert out_template.exists()

    spec = load_template(out_template)
    assert spec.template_id == "generated"
    assert "issue_date" in spec.anchors or "total_amount_gross" in spec.anchors

