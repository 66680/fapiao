from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from invstruct.ocr.base import OcrTextBlock
from invstruct.schemas import FieldProvenance

FieldCandidate = tuple[object, float, FieldProvenance]

_FULLWIDTH_MAP = str.maketrans(
    {
        "：": ":",
        "，": ",",
        "。": ".",
        "；": ";",
        "（": "(",
        "）": ")",
        "－": "-",
        "—": "-",
        "／": "/",
        "　": " ",
        "￥": "¥",
    }
)
_CURRENCY_RE = re.compile(r"(?:RMB|CNY|USD|EUR|¥|￥|\$|€)", re.IGNORECASE)
_AMOUNT_TOKEN_RE = re.compile(
    r"(?:(?:RMB|CNY|USD|EUR)\s*)?[¥￥$€]?\s*-?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d{1,2})?",
    re.IGNORECASE,
)
_INVOICE_VALUE_RE = re.compile(r"[A-Z0-9][A-Z0-9\-]{4,}")
_TAX_VALUE_RE = re.compile(r"[A-Z0-9]{8,20}")


@dataclass
class _Candidate:
    value: object
    score: float
    provenance: FieldProvenance
    reason: str
    tags: set[str] = field(default_factory=set)


def _provenance(block: OcrTextBlock, line_id: int, extractor: str) -> FieldProvenance:
    return FieldProvenance(
        page=block.page,
        bbox=block.bbox,
        extractor=extractor,
        line_id=line_id,
        line_text=block.text,
    )


def normalize_for_rules(text: str, locale: str = "zh-CN") -> str:
    _ = locale
    normalized = text.translate(_FULLWIDTH_MAP)
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\b(No)\s*\.\s*", r"\1. ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"([¥￥$€])\s+(?=\d)", r"\1", normalized)
    normalized = re.sub(r"(?<=\d)\s*[,.]\s*(?=\d)", ".", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    normalized = re.sub(r"(?<=\d)\s*[,]\s*(?=\d{3}\b)", ",", normalized)
    return normalized.strip()


def _normalize_date(value: str) -> date | None:
    text = value.strip()
    patterns = [
        r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})",
        r"(\d{1,2})\.(\d{1,2})\.(20\d{2})",
        r"(\d{1,2})/(\d{1,2})/(20\d{2})",
        r"(\d{1,2})-(\d{1,2})-(20\d{2})",
    ]

    for index, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if not match:
            continue
        nums = [int(item) for item in match.groups()]
        try:
            if index == 0:
                return date(nums[0], nums[1], nums[2])
            if index == 1:
                return date(nums[2], nums[1], nums[0])
            if index == 2:
                month, day, year = nums
                if month > 12 and day <= 12:
                    month, day = day, month
                return date(year, month, day)
            return date(nums[2], nums[1], nums[0])
        except ValueError:
            return None

    zh_match = re.search(r"(20\d{2})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})", text)
    if not zh_match:
        return None
    year, month, day = [int(item) for item in zh_match.groups()]
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_amount_token(token: str) -> float | None:
    cleaned = token.strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"(RMB|CNY|USD|EUR)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("¥", "").replace("￥", "").replace("$", "").replace("€", "")
    cleaned = cleaned.replace(" ", "").replace(",", "")
    if cleaned.count(".") > 1:
        return None
    if not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", cleaned):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if abs(value) >= 1e9:
        return None
    return value


def _amount_from_text(text: str) -> list[tuple[float, str]]:
    values: list[tuple[float, str]] = []
    for match in _AMOUNT_TOKEN_RE.finditer(text):
        token = match.group(0)
        parsed = _parse_amount_token(token)
        if parsed is None:
            continue
        values.append((parsed, token))
    return values


def _has_any(text: str, keywords: set[str]) -> bool:
    return any(item in text for item in keywords)


def _candidate_to_tuple(candidate: _Candidate) -> FieldCandidate:
    return (candidate.value, candidate.score, candidate.provenance)


def _pick_best(candidates: list[_Candidate]) -> _Candidate | None:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            float(item.score),
            float(item.value) if isinstance(item.value, (int, float)) else 0.0,
        ),
    )


def _add_debug_candidate(debug_collector: dict[str, Any] | None, field_name: str, candidate: _Candidate) -> None:
    if debug_collector is None:
        return
    debug_collector.setdefault("candidates", {}).setdefault(field_name, []).append(
        {
            "value": str(candidate.value),
            "confidence": round(float(candidate.score), 4),
            "reason": candidate.reason,
            "tags": sorted(candidate.tags),
            "page": candidate.provenance.page,
            "line_id": candidate.provenance.line_id,
            "line_text": candidate.provenance.line_text,
        }
    )


def _add_debug_selected(debug_collector: dict[str, Any] | None, field_name: str, candidate: _Candidate | None) -> None:
    if debug_collector is None or candidate is None:
        return
    debug_collector.setdefault("selected", {})[field_name] = {
        "value": str(candidate.value),
        "confidence": round(float(candidate.score), 4),
        "reason": candidate.reason,
        "page": candidate.provenance.page,
        "line_id": candidate.provenance.line_id,
        "line_text": candidate.provenance.line_text,
    }


def _clean_identifier_tail(text: str) -> str:
    value = text.strip().strip(":-")
    value = re.sub(r"^[^A-Z0-9]+", "", value, flags=re.IGNORECASE)
    return value.strip()


def _extract_invoice_value(normalized: str) -> str | None:
    match = re.search(
        r"(?:发票(?:号码|号)?|invoice\s*no\.?|no\.?)\s*[:：\-]?\s*([A-Z0-9\-]{5,})",
        normalized,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()
    if not re.search(r"(发票|invoice|no\.?)", normalized, re.IGNORECASE):
        return None
    tail = normalized.split(":")[-1]
    id_match = _INVOICE_VALUE_RE.search(_clean_identifier_tail(tail).upper())
    if id_match:
        return id_match.group(0).upper()
    return None


def _extract_tax_value(normalized: str) -> str | None:
    match = re.search(
        r"(?:纳税人识别号|税号|tax\s*id|tin|vat\s*id|vat)\s*[:：\-]?\s*([A-Z0-9]{8,20})",
        normalized,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()
    if not re.search(r"(税号|tax|tin|vat)", normalized, re.IGNORECASE):
        return None
    tail = normalized.split(":")[-1]
    id_match = _TAX_VALUE_RE.search(_clean_identifier_tail(tail).upper())
    if id_match:
        return id_match.group(0).upper()
    return None


def _limit_debug(debug_collector: dict[str, Any] | None, top_k: int) -> None:
    if debug_collector is None:
        return
    candidates = debug_collector.get("candidates")
    if not isinstance(candidates, dict):
        return
    for field_name, items in candidates.items():
        if not isinstance(items, list):
            continue
        sorted_items = sorted(items, key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        candidates[field_name] = sorted_items[: max(1, top_k)]


def extract_fields(
    blocks: list[OcrTextBlock],
    *,
    locale: str = "zh-CN",
    currency: str = "CNY",
    low_conf: float = 0.75,
    amount_keyword_window: int = 1,
    amount_prefer_keyword: bool = True,
    date_prefer_issue_keywords: bool = True,
    enable_text_normalize: bool = True,
    debug_collector: dict[str, Any] | None = None,
    debug_top_k: int = 5,
) -> dict[str, FieldCandidate]:
    _ = currency
    result: dict[str, FieldCandidate] = {}

    merchant_keywords = {
        "公司",
        "有限",
        "超市",
        "商店",
        "店",
        "酒店",
        "restaurant",
        "store",
        "market",
        "llc",
        "inc",
        "gmbh",
    }
    skip_merchant_keywords = {
        "日期",
        "date",
        "total",
        "amount",
        "tax",
        "发票",
        "invoice",
        "no.",
        "电话",
        "tel",
        "address",
        "地址",
    }
    issue_date_keywords = {"开票日期", "发票日期", "日期", "issue date", "invoice date", "date"}
    bad_date_keywords = {"打印时间", "交易时间", "print time", "transaction", "created at"}
    amount_keywords = {"合计", "总计", "应付", "实付", "total", "amount due", "grand total", "amount"}

    lines: list[dict[str, Any]] = []
    amount_keyword_indices: set[int] = set()
    if debug_collector is not None:
        debug_collector.clear()
        debug_collector["normalized_lines"] = []
        debug_collector["candidates"] = {}
        debug_collector["selected"] = {}

    for index, block in enumerate(blocks):
        raw_text = block.text.strip()
        if not raw_text:
            continue
        normalized = normalize_for_rules(raw_text, locale=locale) if enable_text_normalize else raw_text
        lower_text = normalized.lower()
        lines.append(
            {
                "index": index,
                "block": block,
                "raw_text": raw_text,
                "normalized": normalized,
                "lower_text": lower_text,
            }
        )
        if _has_any(lower_text, amount_keywords):
            amount_keyword_indices.add(index)
        if debug_collector is not None:
            debug_collector["normalized_lines"].append(
                {
                    "index": index,
                    "page": block.page,
                    "raw": raw_text,
                    "normalized": normalized,
                }
            )

    merchant_candidates: list[_Candidate] = []
    date_candidates: list[_Candidate] = []
    amount_candidates: list[_Candidate] = []
    invoice_candidates: list[_Candidate] = []
    tax_candidates: list[_Candidate] = []
    prev_invoice_context = False
    prev_tax_context = False

    for item in lines:
        index = int(item["index"])
        block: OcrTextBlock = item["block"]
        normalized = str(item["normalized"])
        lower_text = str(item["lower_text"])
        has_invoice_keyword = bool(re.search(r"(发票|invoice|no\.?)", lower_text, re.IGNORECASE))
        has_tax_keyword = bool(re.search(r"(税号|纳税人识别号|tax|tin|vat)", lower_text, re.IGNORECASE))

        has_merchant_kw = _has_any(lower_text, merchant_keywords)
        has_skip_kw = _has_any(lower_text, skip_merchant_keywords)
        if (index < 10 and not has_skip_kw) or has_merchant_kw:
            bonus = (0.18 if has_merchant_kw else 0.02) + (0.03 if index < 3 else 0.0)
            score = min(0.96, max(low_conf * 0.9, block.conf + bonus))
            reason = "merchant keyword" if has_merchant_kw else "top region fallback"
            candidate = _Candidate(
                value=normalized,
                score=score,
                provenance=_provenance(block, index, "rules.merchant"),
                reason=reason,
                tags={"keyword"} if has_merchant_kw else {"top_region"},
            )
            merchant_candidates.append(candidate)
            _add_debug_candidate(debug_collector, "merchant_name", candidate)

        normalized_date = _normalize_date(normalized)
        if normalized_date is not None:
            tags = set()
            score = min(0.95, block.conf + 0.05)
            reason_parts = ["date pattern"]
            if date_prefer_issue_keywords and _has_any(lower_text, issue_date_keywords):
                score = min(0.98, score + 0.18)
                tags.add("issue_keyword")
                reason_parts.append("issue keyword")
            if _has_any(lower_text, bad_date_keywords):
                score = max(0.45, score - 0.2)
                tags.add("deprioritized")
                reason_parts.append("time-like deprioritized")
            candidate = _Candidate(
                value=normalized_date,
                score=score,
                provenance=_provenance(block, index, "rules.date"),
                reason=", ".join(reason_parts),
                tags=tags,
            )
            date_candidates.append(candidate)
            _add_debug_candidate(debug_collector, "issue_date", candidate)

        local_has_keyword = _has_any(lower_text, amount_keywords)
        near_keyword = any(abs(index - kw_idx) <= max(0, amount_keyword_window) for kw_idx in amount_keyword_indices)
        for amount_value, raw_token in _amount_from_text(normalized):
            tags = set()
            score = min(0.95, block.conf + 0.03)
            reason_parts = [f"amount token {raw_token}"]
            if local_has_keyword:
                score = min(0.99, score + 0.22)
                tags.add("keyword")
                reason_parts.append("same-line keyword")
            elif near_keyword:
                score = min(0.96, score + 0.12)
                tags.add("near_keyword")
                reason_parts.append("near keyword window")
            if _CURRENCY_RE.search(raw_token):
                score = min(0.99, score + 0.03)
                tags.add("currency_token")
                reason_parts.append("currency token")
            if "." in raw_token:
                score = min(0.99, score + 0.02)
                tags.add("decimal")
            candidate = _Candidate(
                value=amount_value,
                score=score,
                provenance=_provenance(block, index, "rules.amount"),
                reason=", ".join(reason_parts),
                tags=tags,
            )
            amount_candidates.append(candidate)
            _add_debug_candidate(debug_collector, "total_amount_gross", candidate)

        invoice_value = _extract_invoice_value(normalized)
        if invoice_value is None and prev_invoice_context:
            fallback_invoice = _INVOICE_VALUE_RE.search(normalized.upper())
            if fallback_invoice:
                invoice_value = fallback_invoice.group(0).upper()
        if invoice_value:
            reason = "invoice keyword + identifier match"
            if prev_invoice_context and not has_invoice_keyword:
                reason = "invoice context carry-over + identifier match"
            candidate = _Candidate(
                value=invoice_value,
                score=min(0.97, block.conf + 0.13),
                provenance=_provenance(block, index, "rules.invoice"),
                reason=reason,
                tags={"keyword"},
            )
            invoice_candidates.append(candidate)
            _add_debug_candidate(debug_collector, "invoice_number", candidate)
            prev_invoice_context = False
        else:
            prev_invoice_context = has_invoice_keyword

        tax_value = _extract_tax_value(normalized)
        if tax_value is None and prev_tax_context:
            fallback_tax = _TAX_VALUE_RE.search(normalized.upper())
            if fallback_tax:
                tax_value = fallback_tax.group(0).upper()
        if tax_value:
            reason = "tax keyword + identifier match"
            if prev_tax_context and not has_tax_keyword:
                reason = "tax context carry-over + identifier match"
            candidate = _Candidate(
                value=tax_value,
                score=min(0.97, block.conf + 0.13),
                provenance=_provenance(block, index, "rules.tax"),
                reason=reason,
                tags={"keyword"},
            )
            tax_candidates.append(candidate)
            _add_debug_candidate(debug_collector, "merchant_tax_id", candidate)
            prev_tax_context = False
        else:
            prev_tax_context = has_tax_keyword

    picked_merchant = _pick_best(merchant_candidates)
    if picked_merchant:
        result["merchant_name"] = _candidate_to_tuple(picked_merchant)
    elif lines:
        first_line = lines[0]
        first_block: OcrTextBlock = first_line["block"]
        fallback = _Candidate(
            value=str(first_line["normalized"]).strip(),
            score=max(low_conf, min(0.9, first_block.conf)),
            provenance=_provenance(first_block, int(first_line["index"]), "rules.merchant_fallback"),
            reason="first-line fallback",
            tags={"fallback"},
        )
        result["merchant_name"] = _candidate_to_tuple(fallback)
        picked_merchant = fallback
        _add_debug_candidate(debug_collector, "merchant_name", fallback)
    _add_debug_selected(debug_collector, "merchant_name", picked_merchant)

    picked_date = _pick_best(date_candidates)
    if picked_date:
        result["issue_date"] = _candidate_to_tuple(picked_date)
    _add_debug_selected(debug_collector, "issue_date", picked_date)

    if amount_prefer_keyword:
        keyword_amounts = [item for item in amount_candidates if "keyword" in item.tags]
        near_amounts = [item for item in amount_candidates if "near_keyword" in item.tags]
        picked_amount = _pick_best(keyword_amounts) or _pick_best(near_amounts) or _pick_best(amount_candidates)
    else:
        picked_amount = _pick_best(amount_candidates)
    if picked_amount:
        result["total_amount_gross"] = _candidate_to_tuple(picked_amount)
    _add_debug_selected(debug_collector, "total_amount_gross", picked_amount)

    picked_invoice = _pick_best(invoice_candidates)
    if picked_invoice:
        result["invoice_number"] = _candidate_to_tuple(picked_invoice)
    _add_debug_selected(debug_collector, "invoice_number", picked_invoice)

    picked_tax = _pick_best(tax_candidates)
    if picked_tax:
        result["merchant_tax_id"] = _candidate_to_tuple(picked_tax)
    _add_debug_selected(debug_collector, "merchant_tax_id", picked_tax)

    _limit_debug(debug_collector, debug_top_k)
    return result
