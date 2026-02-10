from pathlib import Path

from invstruct.config import AppSettings
from invstruct.pipeline.runner import parse_file


def test_parse_file_has_trace_id_and_stable_sha(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"same-content")

    settings = AppSettings(ocr_engine="mock")
    first = parse_file(sample, config=settings)
    second = parse_file(sample, config=settings)

    assert first.source.trace_id
    assert second.source.trace_id
    assert first.source.trace_id != second.source.trace_id
    assert first.source.sha256 == second.source.sha256

