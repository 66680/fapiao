from invstruct.ocr.base import OcrTextBlock
from invstruct.templates.models import TemplateSpec
from invstruct.templates.registry import TemplateRegistry


def test_registry_selects_matching_doc_type_locale() -> None:
    templates = [
        TemplateSpec(template_id="cn_receipt", version="1.0.0", locale="zh-CN", doc_type="receipt"),
        TemplateSpec(template_id="en_invoice", version="1.0.0", locale="en-US", doc_type="invoice"),
    ]
    registry = TemplateRegistry(templates)
    blocks = [OcrTextBlock(text="小票", bbox=[0, 0, 1, 1], conf=0.9, page=1)]

    selected = registry.select(blocks, doc_type="receipt", locale="zh-CN")
    assert selected is not None
    assert selected.template_id == "cn_receipt"

