from __future__ import annotations

from pathlib import Path
from typing import Any

from invstruct.ocr.base import OcrEngine, OcrTextBlock


class MockOcrEngine(OcrEngine):
    def extract_blocks(
        self,
        file_path: str | Path,
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> list[OcrTextBlock]:
        _ = file_path, trace_id, kwargs
        return [
            OcrTextBlock(text="星河酒店有限公司 STAR HOTEL", bbox=[10, 10, 350, 40], conf=0.98, page=1),
            OcrTextBlock(text="增值税电子普通发票", bbox=[10, 45, 260, 70], conf=0.97, page=1),
            OcrTextBlock(text="开票日期: 2026年2月9日", bbox=[10, 80, 260, 110], conf=0.95, page=1),
            OcrTextBlock(text="发票号: 202602090001", bbox=[10, 115, 260, 145], conf=0.94, page=1),
            OcrTextBlock(text="纳税人识别号: 91350100MA12345678", bbox=[10, 150, 360, 180], conf=0.93, page=1),
            OcrTextBlock(text="价税合计: ¥123.45", bbox=[10, 185, 240, 215], conf=0.96, page=1),
            OcrTextBlock(text="Total Amount: 123.45", bbox=[10, 220, 260, 245], conf=0.92, page=1),
        ]
