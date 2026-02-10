import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_batch_fixtures_engine_roundtrip(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "a.png").write_bytes(b"fake-a")
    (input_dir / "b.png").write_bytes(b"fake-b")

    (input_dir / "a.blocks.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {"text": "Store A", "bbox": [10, 10, 180, 40], "conf": 0.9, "page": 1},
                    {"text": "Date 2026-02-09", "bbox": [10, 45, 200, 70], "conf": 0.9, "page": 1},
                    {"text": "Total Amount: 100.00", "bbox": [10, 80, 220, 105], "conf": 0.95, "page": 1},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (input_dir / "b.blocks.json").write_text(
        json.dumps(
            {
                "blocks": [
                    {"text": "Store B", "bbox": [10, 10, 180, 40], "conf": 0.9, "page": 1},
                    {"text": "Date 2026/02/10", "bbox": [10, 45, 200, 70], "conf": 0.9, "page": 1},
                    {"text": "Total Amount: 200.50", "bbox": [10, 80, 220, 105], "conf": 0.95, "page": 1},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(app, ["batch", str(input_dir), "--out", str(out_dir), "--ocr-engine", "fixtures"])
    assert result.exit_code == 0

    report = json.loads(result.stdout)
    assert report["summary"]["success"] == 2
    assert report["summary"]["skipped"] == 0
    assert report["summary"]["failed"] == 0

    records = [json.loads(line) for line in (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert len(records) == 2
    assert {item["status"] for item in records} == {"success"}
