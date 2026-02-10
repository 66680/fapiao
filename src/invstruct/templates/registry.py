from __future__ import annotations

from invstruct.ocr.base import OcrTextBlock
from invstruct.templates.models import TemplateSpec


class TemplateRegistry:
    def __init__(self, templates: list[TemplateSpec]) -> None:
        self.templates = templates

    def select(self, blocks: list[OcrTextBlock], doc_type: str, locale: str) -> TemplateSpec | None:
        _ = blocks
        candidates = [item for item in self.templates if item.doc_type == doc_type and item.locale == locale]
        if candidates:
            return candidates[0]
        fallback = [item for item in self.templates if item.doc_type == doc_type]
        if fallback:
            return fallback[0]
        return self.templates[0] if self.templates else None

    def get(self, template_id: str) -> TemplateSpec | None:
        for template in self.templates:
            if template.template_id == template_id:
                return template
        return None

