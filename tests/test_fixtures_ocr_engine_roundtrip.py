import json
from pathlib import Path

from typer.testing import CliRunner

from invstruct.cli import app


def test_fixtures_ocr_engine_roundtrip(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image")
    blocks = {
        "blocks": [
            {"text": "My Store LLC", "bbox": [10, 10, 220, 40], "conf": 0.98, "page": 1},
            {"text": "Invoice No: INV-2026-0001", "bbox": [10, 45, 280, 70], "conf": 0.95, "page": 1},
            {"text": "Tax ID: 91350100MA12345678", "bbox": [10, 75, 320, 100], "conf": 0.95, "page": 1},
            {"text": "Date 2026-02-09", "bbox": [10, 105, 220, 130], "conf": 0.96, "page": 1},
            {"text": "Total Amount: 188.60", "bbox": [10, 135, 260, 160], "conf": 0.97, "page": 1},
        ]
    }
    (tmp_path / "sample.blocks.json").write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["parse", str(sample), "--ocr-engine", "fixtures"])
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["issue_date"] == "2026-02-09"
    assert payload["total_amount_gross"] == 188.6
    assert payload["source"]["trace_id"]
    assert len(payload["source"]["sha256"]) == 64
    assert payload["provenance"]["total_amount_gross"]["page"] == 1
    assert payload["provenance"]["total_amount_gross"]["line_text"]
