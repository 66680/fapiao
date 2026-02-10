from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class OcrTextBlock(BaseModel):
    text: str
    bbox: list[float] = Field(default_factory=list)
    conf: float = 0.0
    page: int = 1
    line_id: str | int | None = None
    line_text: str | None = None


class OcrEngine(ABC):
    def get_warnings(self) -> list[dict[str, Any]]:
        return []

    @abstractmethod
    def extract_blocks(
        self,
        file_path: str | Path,
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> list[OcrTextBlock]:
        raise NotImplementedError

    def recognize(self, file_path: str | Path) -> list[OcrTextBlock]:
        return self.extract_blocks(file_path)
