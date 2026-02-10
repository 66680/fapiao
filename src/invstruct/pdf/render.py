from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

from invstruct.errors import ErrorCode, InputError


def render_pdf_to_images(pdf_path: Path, max_pages: int, trace_id: str) -> list[Path]:
    try:
        pdfium = importlib.import_module("pypdfium2")
        pil_image_module = importlib.import_module("PIL.Image")
    except ModuleNotFoundError as exc:
        raise InputError(
            ErrorCode.E1001,
            "PDF rendering dependency missing, install invstruct[pdf].",
            trace_id,
            {"missing": str(exc)},
        ) from exc

    _ = pil_image_module
    doc = pdfium.PdfDocument(str(pdf_path))
    page_count = min(len(doc), max_pages)
    output_paths: list[Path] = []

    for index in range(page_count):
        page = doc[index]
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        tmp = tempfile.NamedTemporaryFile(suffix=f"_p{index + 1}.png", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        pil_image.save(tmp_path, format="PNG")
        output_paths.append(tmp_path)

    return output_paths

