from pathlib import Path

import pytest

from invstruct.config import AppSettings
from invstruct.errors import ErrorCode, InputError
from invstruct.pipeline.runner import parse_path


def test_pdf_render_missing_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample_pdf = tmp_path / "sample.pdf"
    sample_pdf.write_bytes(b"%PDF-1.4\n%fake\n")

    import invstruct.pdf.render as render_module

    real_import = render_module.importlib.import_module

    def fake_import(name: str):
        if name in {"pypdfium2", "PIL.Image"}:
            raise ModuleNotFoundError(f"No module named {name}")
        return real_import(name)

    monkeypatch.setattr(render_module.importlib, "import_module", fake_import)

    settings = AppSettings(ocr_engine="mock", pdf_mode="merge")
    with pytest.raises(InputError) as exc_info:
        parse_path(sample_pdf, trace_id="trace-pdf-missing", settings=settings)

    exc = exc_info.value
    assert exc.code == ErrorCode.E1001
    assert "invstruct[pdf]" in exc.message

