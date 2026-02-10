from pathlib import Path

from invstruct.config import AppSettings
from invstruct.pipeline.runner import parse_path


def test_template_chain_falls_back_to_common(tmp_path: Path) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake")

    settings = AppSettings(template_dir="configs/templates", locale="zh-CN", ocr_engine="mock")
    record = parse_path(sample, trace_id="chain-trace", settings=settings)

    assert record.total_amount_gross is not None
    assert record.merchant_name is not None

