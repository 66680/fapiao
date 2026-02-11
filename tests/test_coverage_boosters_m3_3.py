from __future__ import annotations

import json
from pathlib import Path

import pytest

from invstruct.export.manifest import _find_dedup_profile, build_export_manifest, write_export_manifest
from invstruct.ocr.base import OcrEngine, OcrTextBlock
from invstruct.ocr.fixtures import FixturesOcrEngine, _as_float, _as_int, _load_blocks_json, _load_blocks_jsonl
from invstruct.pipeline.mock_pipeline import parse_with_mock
from invstruct.validators.engine import run_validators


class _DummyEngine(OcrEngine):
    def extract_blocks(self, file_path: str | Path, trace_id: str | None = None, **kwargs):
        _ = file_path, trace_id, kwargs
        return [OcrTextBlock(text="x", bbox=[0, 0, 1, 1], conf=1.0, page=1)]


def test_ocr_base_recognize_delegates_extract_blocks():
    engine = _DummyEngine()
    blocks = engine.recognize("any.png")
    assert len(blocks) == 1
    assert blocks[0].text == "x"


def test_mock_pipeline_outputs_trace_and_hash(tmp_path: Path):
    sample = tmp_path / "a.png"
    sample.write_bytes(b"abc")
    record = parse_with_mock(sample, "trace-m3-3")
    dumped = record.to_dict()
    assert dumped["source"]["trace_id"] == "trace-m3-3"
    assert dumped["source"]["file_name"] == "a.png"
    assert len(dumped["source"]["sha256"]) == 64


def test_manifest_helpers_cover_missing_and_invalid(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    records.write_text("{}\n", encoding="utf-8")
    assert _find_dedup_profile(records) is None

    report = tmp_path / "merge_report.json"
    report.write_text("not-json", encoding="utf-8")
    assert _find_dedup_profile(records) is None

    report.write_text(json.dumps({"dedup_profile": ""}), encoding="utf-8")
    assert _find_dedup_profile(records) is None

    report.write_text(json.dumps({"dedup_profile": "invoice+tax+amount"}), encoding="utf-8")
    assert _find_dedup_profile(records) == "invoice+tax+amount"

    payload = build_export_manifest(
        input_records_path=records,
        row_count=1,
        columns=["doc_id"],
        outputs={"csv": "out.csv"},
    )
    out = tmp_path / "nested" / "manifest.json"
    write_export_manifest(out, payload)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["row_count"] == 1
    assert loaded["outputs"]["csv"] == "out.csv"


def test_fixtures_ocr_helpers_cover_conversion_and_json_parsers(tmp_path: Path):
    assert _as_float("1.2") == 1.2
    assert _as_float("bad", 0.7) == 0.7
    assert _as_int("3") == 3
    assert _as_int("bad", 9) == 9

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")
    assert _load_blocks_json(bad_json) is None

    wrong_shape = tmp_path / "wrong.json"
    wrong_shape.write_text(json.dumps({"x": 1}), encoding="utf-8")
    assert _load_blocks_json(wrong_shape) is None

    map_file = tmp_path / "map.jsonl"
    map_file.write_text("\nnot-json\n{}\n", encoding="utf-8")
    assert _load_blocks_jsonl(map_file, "sample.png") is None


def test_fixtures_ocr_engine_jsonl_loading_and_warning_paths(tmp_path: Path):
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"img")

    mapping = {
        "source_file": "sample.png",
        "blocks": [{"text": "TOTAL", "bbox": [1, 2, 3, 4], "conf": "0.8", "page": "2"}],
    }
    (tmp_path / ".invstruct.blocks.jsonl").write_text(json.dumps(mapping), encoding="utf-8")

    engine = FixturesOcrEngine(fixtures_dir=tmp_path)
    blocks = engine.extract_blocks(sample)
    assert len(blocks) == 1
    assert blocks[0].text == "TOTAL"
    assert blocks[0].page == 2
    assert blocks[0].line_text == "TOTAL"

    empty_sample = tmp_path / "sub" / "missing.png"
    empty_sample.parent.mkdir(parents=True, exist_ok=True)
    empty_sample.write_bytes(b"img")

    empty_engine = FixturesOcrEngine(fixtures_dir=tmp_path / "not-found")
    missing = empty_engine.extract_blocks(empty_sample)
    assert missing == []
    warnings = empty_engine.get_warnings()
    assert warnings and warnings[0]["code"] == "fixtures_missing"


def test_validators_cover_remaining_branches():
    record = {
        "a": 10,
        "b": 2,
        "c": "ok",
        "d": "invoice-2026",
        "missing": None,
    }
    validators = [
        {"type": "required", "field": "missing", "severity": "critical"},
        {"type": "lt", "field": "a", "value": 3, "severity": "warning"},
        {"type": "eq", "field": "c", "value": "nope", "severity": "warning"},
        {"type": "regex", "field": "d", "pattern": r"^inv-", "severity": "warning"},
    ]

    issues = run_validators(record, validators)
    issue_types = {item["type"] for item in issues}
    assert {"required", "lt", "eq", "regex"}.issubset(issue_types)


def test_validators_gt_and_regex_none_pattern():
    record = {"amount": 1.0, "text": "abc"}
    issues = run_validators(
        record,
        [
            {"type": "gt", "field": "amount", "value": 3, "severity": "critical"},
            {"type": "regex", "field": "text", "pattern": None, "severity": "warning"},
        ],
    )
    assert len(issues) == 2
