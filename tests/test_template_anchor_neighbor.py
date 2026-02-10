from invstruct.extractors.template_extractor import extract_fields_with_template
from invstruct.ocr.base import OcrTextBlock
from invstruct.templates.models import AnchorRule, ScoringRule, TemplateSpec


def test_anchor_neighbor_selects_right_value() -> None:
    spec = TemplateSpec(
        template_id="cn_anchor",
        version="1.0.0",
        locale="zh-CN",
        doc_type="receipt",
        aliases={"total_amount_gross": ["价税合计"]},
        regex={"total_amount_gross": r"([¥￥]?\s?\d+[\.,]?\d{0,2})"},
        anchors={
            "total_amount_gross": AnchorRule(
                keywords=["价税合计"],
                roi=[0.0, 0.0, 1.0, 1.0],
                direction="right",
            )
        },
        scoring=ScoringRule(ocr_conf_weight=0.4, regex_weight=0.3, layout_weight=0.3),
    )
    blocks = [
        OcrTextBlock(text="价税合计", bbox=[10, 100, 80, 120], conf=0.99, page=1),
        OcrTextBlock(text="¥123.45", bbox=[90, 100, 140, 120], conf=0.97, page=1),
    ]

    extracted = extract_fields_with_template(blocks, spec)
    assert extracted["total_amount_gross"][0].replace(" ", "") in {"¥123.45", "123.45"}
    assert extracted["total_amount_gross"][2].extractor == "template:cn_anchor"

