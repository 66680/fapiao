from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from invstruct.errors import ErrorCode, InputError
from invstruct.ocr.base import OcrTextBlock


@dataclass
class PdfParseResult:
    blocks: list[OcrTextBlock]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    parser_version: str = "pdfplumber@unknown"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _word_x0(word: dict[str, Any]) -> float:
    value = word.get("x0")
    return float(value) if _is_number(value) else 0.0


def _word_x1(word: dict[str, Any]) -> float:
    value = word.get("x1")
    if _is_number(value):
        return float(value)
    x0 = word.get("x0")
    return float(x0) if _is_number(x0) else 0.0


def _word_top(word: dict[str, Any]) -> float | None:
    for key in ("doctop", "top"):
        value = word.get(key)
        if _is_number(value):
            return float(value)
    return None


def _word_bottom(word: dict[str, Any]) -> float | None:
    for key in ("bottom",):
        value = word.get(key)
        if _is_number(value):
            return float(value)
    return None


def _word_text(word: dict[str, Any]) -> str:
    return str(word.get("text", "")).strip()


def _contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9FFF]", value))


def _contains_latin_or_digit(value: str) -> bool:
    return bool(re.search(r"[A-Za-z0-9]", value))


def _join_tokens(tokens: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    prev_x1: float | None = None
    prev_text = ""

    for token in tokens:
        current = _word_text(token)
        if not current:
            continue
        x0 = _word_x0(token)
        gap = (x0 - prev_x1) if prev_x1 is not None else 0.0

        should_add_space = False
        if parts:
            prev_last = prev_text[-1:] if prev_text else ""
            curr_first = current[:1]
            if prev_last in {"¥", "￥", "$", "€"} or curr_first in {"¥", "￥", "$", "€"}:
                should_add_space = False
            elif _contains_latin_or_digit(prev_text) and _contains_latin_or_digit(current):
                should_add_space = True
            elif _contains_cjk(prev_text) and _contains_cjk(current):
                should_add_space = False
            elif gap >= 12.0:
                should_add_space = True
            elif gap >= 3.0 and (_contains_latin_or_digit(prev_text) or _contains_latin_or_digit(current)):
                should_add_space = True

        if should_add_space:
            parts.append(" ")
        parts.append(current)
        prev_text = current
        prev_x1 = _word_x1(token)

    return "".join(parts).strip()


def _merge_bbox(tokens: list[dict[str, Any]]) -> list[float]:
    x0_values = [_word_x0(item) for item in tokens]
    x1_values = [_word_x1(item) for item in tokens]
    top_values = [value for value in (_word_top(item) for item in tokens) if value is not None]
    bottom_values = [value for value in (_word_bottom(item) for item in tokens) if value is not None]
    if not x0_values or not x1_values or not top_values or not bottom_values:
        return []
    return [min(x0_values), min(top_values), max(x1_values), max(bottom_values)]


def _words_to_line_blocks(words: list[dict[str, Any]], page_index: int, *, y_tol: float = 3.0) -> list[OcrTextBlock]:
    if not words:
        return []

    normalized_words = []
    for word in words:
        if not _word_text(word):
            continue
        top_value = _word_top(word)
        if top_value is None:
            continue
        normalized_words.append(word)
    if not normalized_words:
        return []

    sorted_words = sorted(normalized_words, key=lambda item: (_word_top(item) or 0.0, _word_x0(item)))
    rows: list[list[dict[str, Any]]] = []
    current_row: list[dict[str, Any]] = []
    current_top: float | None = None

    for word in sorted_words:
        word_top = _word_top(word)
        if word_top is None:
            continue
        if not current_row:
            current_row = [word]
            current_top = word_top
            continue
        if current_top is not None and abs(word_top - current_top) <= y_tol:
            current_row.append(word)
            current_top = (current_top * (len(current_row) - 1) + word_top) / len(current_row)
            continue
        rows.append(current_row)
        current_row = [word]
        current_top = word_top
    if current_row:
        rows.append(current_row)

    blocks: list[OcrTextBlock] = []
    for row_words in rows:
        ordered = sorted(row_words, key=_word_x0)
        line_text = _join_tokens(ordered)
        if not line_text:
            continue
        blocks.append(OcrTextBlock(text=line_text, bbox=_merge_bbox(ordered), conf=1.0, page=page_index))

    return blocks


def _words_to_raw_blocks(words: list[dict[str, Any]], page_index: int) -> list[OcrTextBlock]:
    blocks: list[OcrTextBlock] = []
    for word in sorted(words, key=lambda item: (_word_top(item) or 0.0, _word_x0(item))):
        text = _word_text(word)
        if not text:
            continue
        blocks.append(OcrTextBlock(text=text, bbox=_merge_bbox([word]), conf=1.0, page=page_index))
    return blocks


def parse_pdf_text_blocks(
    path: str | Path,
    trace_id: str,
    *,
    enable_line_merge: bool = True,
    line_merge_y_tol: float = 3.0,
) -> PdfParseResult:
    try:
        pdfplumber = importlib.import_module("pdfplumber")
    except ModuleNotFoundError as exc:
        raise InputError(
            ErrorCode.E3001,
            "PDF text dependency missing, install invstruct[pdf].",
            trace_id,
            {"missing": str(exc), "status": "skipped"},
        ) from exc

    parser_version = f"pdfplumber@{getattr(pdfplumber, '__version__', 'unknown')}"
    file_path = Path(path)
    blocks: list[OcrTextBlock] = []
    warnings: list[dict[str, Any]] = []

    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                try:
                    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False) or []
                except Exception as exc:  # noqa: BLE001
                    warnings.append(
                        {
                            "page_index": page_index,
                            "reason": "page_extract_failed",
                            "exception_name": exc.__class__.__name__,
                            "message": str(exc),
                        }
                    )
                    continue

                line_blocks = (
                    _words_to_line_blocks(words, page_index, y_tol=line_merge_y_tol)
                    if enable_line_merge
                    else _words_to_raw_blocks(words, page_index)
                )
                if line_blocks:
                    blocks.extend(line_blocks)
                    continue

                try:
                    text = page.extract_text() or ""
                except Exception as exc:  # noqa: BLE001
                    warnings.append(
                        {
                            "page_index": page_index,
                            "reason": "page_extract_failed",
                            "exception_name": exc.__class__.__name__,
                            "message": str(exc),
                        }
                    )
                    continue

                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines:
                    warnings.append(
                        {
                            "page_index": page_index,
                            "reason": "no_text",
                            "exception_name": None,
                            "message": "No extractable text on page",
                        }
                    )
                    continue
                for line in lines:
                    blocks.append(OcrTextBlock(text=line, bbox=[], conf=1.0, page=page_index))
    except InputError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise InputError(
            ErrorCode.E3002,
            "PDF parse failed",
            trace_id,
            {"status": "failed", "exception_name": exc.__class__.__name__, "message": str(exc), "parser_version": parser_version},
        ) from exc

    return PdfParseResult(blocks=blocks, warnings=warnings, parser_version=parser_version)
