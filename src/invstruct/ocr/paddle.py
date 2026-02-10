from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from invstruct.errors import ErrorCode, OcrError
from invstruct.ocr.base import OcrEngine, OcrTextBlock


class PaddleOcrEngine(OcrEngine):
    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self._ocr = None

    def _load(self):
        if self._ocr is not None:
            return self._ocr
        try:
            paddle_module = importlib.import_module("paddleocr")
        except ModuleNotFoundError as exc:
            raise OcrError(
                ErrorCode.E2001,
                "PaddleOCR dependency missing, install invstruct[paddle] and platform-specific paddlepaddle first.",
                self.trace_id,
                {"missing": "paddleocr"},
            ) from exc

        ocr_cls = getattr(paddle_module, "PaddleOCR", None)
        if ocr_cls is None:
            raise OcrError(ErrorCode.E2001, "Invalid paddleocr installation: PaddleOCR not found.", self.trace_id)
        self._ocr = ocr_cls(use_angle_cls=True, lang="ch")
        return self._ocr

    def extract_blocks(
        self,
        file_path: str | Path,
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> list[OcrTextBlock]:
        _ = trace_id, kwargs
        engine = self._load()
        result = engine.ocr(str(file_path), cls=True)
        blocks: list[OcrTextBlock] = []
        for page_items in result or []:
            for item in page_items or []:
                points = item[0] if item and len(item) > 0 else []
                text_conf = item[1] if item and len(item) > 1 else ["", 0.0]
                text = str(text_conf[0]) if text_conf else ""
                conf = float(text_conf[1]) if len(text_conf) > 1 else 0.0
                flat_bbox = [float(v) for point in points for v in point] if points else []
                blocks.append(OcrTextBlock(text=text, bbox=flat_bbox, conf=conf, page=1))
        return blocks
