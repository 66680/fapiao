from pathlib import Path

from invstruct.config import AppSettings
from invstruct.pipeline.runner import parse_file


def test_retry_key_is_deterministic_for_same_file(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"same-content")

    settings = AppSettings(ocr_engine="mock")
    first = parse_file(sample, config=settings)
    second = parse_file(sample, config=settings)

    assert first.retry_key
    assert first.retry_key == second.retry_key

    sample.write_bytes(b"changed-content")
    third = parse_file(sample, config=settings)
    assert third.retry_key
    assert third.retry_key != first.retry_key

