from __future__ import annotations

import re
from typing import Any

from invstruct.ocr.base import OcrTextBlock
from invstruct.schemas import FieldProvenance

FieldCandidate = tuple[str, float, FieldProvenance]


def _build_candidate(block: OcrTextBlock, value: str, boost: float = 0.0) -> FieldCandidate:
    score = min(1.0, max(0.0, block.conf + boost))
    provenance = FieldProvenance(page=block.page, bbox=block.bbox, extractor="common_rules")
    return value.strip(), score, provenance


def _best(candidates: list[FieldCandidate]) -> FieldCandidate | None:
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])


def extract_fields(blocks: list[OcrTextBlock]) -> dict[str, FieldCandidate]:
    issue_date_candidates: list[FieldCandidate] = []
    total_candidates: list[FieldCandidate] = []
    tax_id_candidates: list[FieldCandidate] = []
    invoice_no_candidates: list[FieldCandidate] = []
    merchant_candidates: list[FieldCandidate] = []

    date_re = re.compile(r"(20\d{2}(?:[-/]\d{1,2}[-/]\d{1,2}|年\d{1,2}月\d{1,2}日))")
    tax_id_re = re.compile(r"([0-9A-Z]{15,20})")
    invoice_re = re.compile(r"(?:发票号|invoice\s*no\.?|no\.?)\s*[:：]?\s*(\d{6,})", re.IGNORECASE)
    amount_re = re.compile(r"([¥￥]?\s*\d+[\.,]?\d{0,2})")

    merchant_keywords = ("有限公司", "超市", "酒店", "STORE")
    skip_keywords = ("开票", "日期", "发票", "税号", "识别号", "合计", "total", "amount")

    for index, block in enumerate(blocks):
        text = block.text.strip()
        if not text:
            continue

        date_match = date_re.search(text)
        if date_match:
            issue_date_candidates.append(_build_candidate(block, date_match.group(1), boost=0.03))

        if any(keyword in text.lower() for keyword in ("合计", "总计", "价税合计", "total", "amount")):
            amount_match = amount_re.search(text)
            if amount_match:
                total_candidates.append(_build_candidate(block, amount_match.group(1), boost=0.05))

        if any(keyword in text for keyword in ("税号", "纳税人识别号")):
            tax_match = tax_id_re.search(text)
            if tax_match:
                tax_id_candidates.append(_build_candidate(block, tax_match.group(1), boost=0.03))

        invoice_match = invoice_re.search(text)
        if invoice_match:
            invoice_no_candidates.append(_build_candidate(block, invoice_match.group(1), boost=0.04))

        is_top = index <= 2
        has_merchant_keyword = any(keyword in text for keyword in merchant_keywords)
        has_skip_keyword = any(keyword in text.lower() for keyword in [token.lower() for token in skip_keywords])
        if (is_top or has_merchant_keyword) and not has_skip_keyword and len(text) >= 4:
            merchant_candidates.append(_build_candidate(block, text, boost=0.02 if has_merchant_keyword else 0.0))

    extracted: dict[str, FieldCandidate] = {}
    selections: dict[str, FieldCandidate | None] = {
        "merchant_name": _best(merchant_candidates),
        "issue_date": _best(issue_date_candidates),
        "total_amount_gross": _best(total_candidates),
        "merchant_tax_id": _best(tax_id_candidates),
        "invoice_number": _best(invoice_no_candidates),
    }
    for key, value in selections.items():
        if value is not None:
            extracted[key] = value
    return extracted

