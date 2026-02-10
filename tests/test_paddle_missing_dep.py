from pathlib import Path

import pytest

from invstruct.config import AppSettings
from invstruct.errors import ErrorCode, OcrError
from invstruct.pipeline.runner import parse_path


def test_paddle_engine_missing_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "sample.png"
    sample.write_bytes(b"fake-image-content")

    import invstruct.ocr.paddle as paddle_module

    real_import = paddle_module.importlib.import_module

    def fake_import(name: str):
        if name == "paddleocr":
            raise ModuleNotFoundError("No module named paddleocr")
        return real_import(name)

    monkeypatch.setattr(paddle_module.importlib, "import_module", fake_import)

    settings = AppSettings(ocr_engine="paddle")
    with pytest.raises(OcrError) as exc_info:
        parse_path(sample, trace_id="trace-paddle-missing", settings=settings)

    exc = exc_info.value
    assert exc.code == ErrorCode.E2001
    envelope = exc.to_envelope().model_dump(mode="json")
    assert envelope["error"]["code"] == ErrorCode.E2001

