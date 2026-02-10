from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Literal

from invstruct.config import AppSettings
from invstruct.errors import ErrorCode, InputError
from invstruct.extractors.rules import extract_fields
from invstruct.extractors.template_extractor import extract_fields_with_template
from invstruct.normalize.common import normalize_amount, normalize_date
from invstruct.ocr.base import OcrEngine, OcrTextBlock
from invstruct.ocr.fixtures import FixturesOcrEngine
from invstruct.ocr.mock import MockOcrEngine
from invstruct.ocr.paddle import PaddleOcrEngine
from invstruct.pdf.base import parse_pdf_text_blocks
from invstruct.pdf.render import render_pdf_to_images
from invstruct.schemas import Confidence, InvoiceRecord, SourceInfo
from invstruct.templates.loader import load_templates
from invstruct.templates.registry import TemplateRegistry
from invstruct.utils.hash import build_retry_key, sha256_file
from invstruct.validators.engine import run_validators


def build_error_record(
    path: str | Path,
    *,
    trace_id: str,
    sha256: str,
    status: Literal["failed", "skipped"] = "skipped",
    code: ErrorCode | str = ErrorCode.E3001,
    message: str = "PDF not supported yet",
    retry_key: str | None = None,
    parser_version: str | None = None,
    warnings: list[dict] | None = None,
) -> InvoiceRecord:
    file_name = Path(path).name
    code_value = code.value if isinstance(code, ErrorCode) else str(code)
    return InvoiceRecord(
        doc_id=str(uuid.uuid4()),
        doc_type="unknown",
        source=SourceInfo(file_name=file_name, sha256=sha256, trace_id=trace_id),
        provenance={},
        status=status,
        error_code=code_value,
        error_message=message,
        retry_key=retry_key,
        parser_version=parser_version,
        warnings=warnings,
    )


def build_skipped_record(
    path: str | Path,
    *,
    trace_id: str,
    sha256: str,
    code: ErrorCode | str = ErrorCode.E3001,
    message: str = "PDF not supported yet",
    retry_key: str | None = None,
    parser_version: str | None = None,
    warnings: list[dict] | None = None,
) -> InvoiceRecord:
    return build_error_record(
        path,
        trace_id=trace_id,
        sha256=sha256,
        status="skipped",
        code=code,
        message=message,
        retry_key=retry_key,
        parser_version=parser_version,
        warnings=warnings,
    )


def _classify_doc_type(texts: str) -> str:
    if "增值税" in texts:
        return "vat_invoice"
    if "发票" in texts:
        return "invoice"
    if texts.strip():
        return "receipt"
    return "unknown"


def _soft_validate(confidence: dict[str, float], required: tuple[str, ...]) -> float:
    if not required:
        return 0.0
    penalty = 0.0
    values = []
    for field_name in required:
        if field_name not in confidence:
            penalty += 0.15
            continue
        values.append(confidence[field_name])
    if not values:
        return max(0.0, 0.2 - penalty)
    base = sum(values) / len(values)
    return max(0.0, min(1.0, base - penalty))


def _select_engine(settings: AppSettings, trace_id: str, override_engine: OcrEngine | None) -> OcrEngine:
    if override_engine is not None:
        return override_engine
    selected = settings.ocr_engine.lower().strip()
    if selected == "paddle":
        return PaddleOcrEngine(trace_id=trace_id)
    if selected == "fixtures":
        return FixturesOcrEngine()
    return MockOcrEngine()


def _extract_with_chain(
    blocks: list[OcrTextBlock],
    settings: AppSettings,
    doc_type: str,
    template_id: str | None,
    debug_info: dict[str, object] | None = None,
) -> tuple[dict, str | None, list[dict]]:
    templates = load_templates(settings.template_dir)
    registry = TemplateRegistry(templates)
    selected_template = registry.get(template_id) if template_id else registry.select(blocks, doc_type, settings.locale)

    extracted: dict = {}
    validators: list[dict] = []
    used_template_id: str | None = None

    if selected_template is not None:
        used_template_id = selected_template.template_id
        validators = selected_template.validators
        extracted.update(extract_fields_with_template(blocks, selected_template))

    rules_fields = extract_fields(
        blocks,
        locale=settings.locale,
        currency=settings.currency,
        low_conf=settings.low_conf,
        amount_keyword_window=settings.rules_amount_keyword_window,
        amount_prefer_keyword=settings.rules_amount_prefer_keyword,
        date_prefer_issue_keywords=settings.rules_date_prefer_issue_keywords,
        enable_text_normalize=settings.rules_enable_text_normalize,
        debug_collector=debug_info,
        debug_top_k=settings.rules_debug_top_k,
    )
    for key, value in rules_fields.items():
        extracted.setdefault(key, value)

    return extracted, used_template_id, validators


def _build_record(
    blocks: list[OcrTextBlock],
    source_hash: str,
    retry_key: str,
    source_file_name: str,
    trace_id: str,
    settings: AppSettings,
    template_id: str | None,
    parser_version: str,
    warnings: list[dict] | None = None,
    debug_info: dict[str, object] | None = None,
) -> InvoiceRecord:
    joined_text = "\n".join(block.text for block in blocks)
    doc_type = _classify_doc_type(joined_text)
    extracted, used_template_id, validators = _extract_with_chain(
        blocks,
        settings,
        doc_type,
        template_id,
        debug_info=debug_info,
    )

    issue_date_raw = extracted.get("issue_date", (None, 0.0, None))[0]
    amount_raw = extracted.get("total_amount_gross", (None, 0.0, None))[0]
    normalized_issue_date = issue_date_raw if hasattr(issue_date_raw, "year") else normalize_date(issue_date_raw)
    normalized_amount = amount_raw if isinstance(amount_raw, (int, float)) else normalize_amount(amount_raw)

    field_conf = {field_name: data[1] for field_name, data in extracted.items()}
    overall_conf = _soft_validate(field_conf, ("merchant_name", "issue_date", "total_amount_gross"))
    provenance = {field_name: data[2] for field_name, data in extracted.items()}

    record = InvoiceRecord(
        doc_id=str(uuid.uuid4()),
        doc_type=doc_type,
        template_id=used_template_id,
        issue_date=normalized_issue_date,
        merchant_name=extracted.get("merchant_name", (None, 0.0, None))[0],
        merchant_tax_id=extracted.get("merchant_tax_id", (None, 0.0, None))[0],
        invoice_number=extracted.get("invoice_number", (None, 0.0, None))[0],
        currency=settings.currency,
        total_amount_gross=normalized_amount,
        confidence=Confidence(overall=overall_conf, fields=field_conf),
        provenance=provenance,
        retry_key=retry_key,
        parser_version=parser_version,
        warnings=warnings or None,
        source=SourceInfo(file_name=source_file_name, sha256=source_hash, trace_id=trace_id),
    )

    issues = run_validators(record.to_dict(), validators)
    if issues:
        critical = sum(1 for issue in issues if issue.get("severity") == "critical")
        record.confidence.overall = max(0.0, record.confidence.overall - (0.15 * critical) - (0.05 * (len(issues) - critical)))
        record.validation_issues = issues

    return record


def parse_path(
    path: str | Path,
    trace_id: str,
    settings: AppSettings,
    ocr_engine: OcrEngine | None = None,
    source_file_name: str | None = None,
    template_id: str | None = None,
    allow_pdf: bool | None = None,
    debug_info: dict[str, object] | None = None,
) -> InvoiceRecord:
    file_path = Path(path)
    if not file_path.exists():
        raise InputError(ErrorCode.E1001, "Input file not found", trace_id, {"path": str(file_path)})

    source_hash = sha256_file(file_path)
    retry_key = build_retry_key(file_path, source_hash)
    record_source_name = source_file_name or file_path.name

    if file_path.suffix.lower() == ".pdf":
        if allow_pdf is False:
            raise InputError(
                ErrorCode.E3001,
                "PDF not supported yet",
                trace_id,
                {"path": str(file_path), "filename": file_path.name, "status": "skipped"},
            )
        if allow_pdf is True:
            parse_result = parse_pdf_text_blocks(
                file_path,
                trace_id,
                enable_line_merge=settings.pdf_enable_line_merge,
                line_merge_y_tol=settings.pdf_line_merge_y_tol,
            )
            if not parse_result.blocks:
                raise InputError(
                    ErrorCode.E3002,
                    "PDF has no extractable text",
                    trace_id,
                    {
                        "path": str(file_path),
                        "filename": file_path.name,
                        "status": "skipped",
                        "parser_version": parse_result.parser_version,
                        "warnings": parse_result.warnings,
                    },
                )
            return _build_record(
                parse_result.blocks,
                source_hash,
                retry_key,
                record_source_name,
                trace_id,
                settings,
                template_id,
                parser_version=parse_result.parser_version,
                warnings=parse_result.warnings,
                debug_info=debug_info,
            )

    engine = _select_engine(settings, trace_id, ocr_engine)

    if file_path.suffix.lower() == ".pdf" and settings.pdf_mode == "merge":
        image_paths = render_pdf_to_images(file_path, settings.max_pdf_pages, trace_id)
        try:
            merged_blocks: list[OcrTextBlock] = []
            for page_index, image_path in enumerate(image_paths, start=1):
                page_blocks = engine.extract_blocks(image_path, trace_id=trace_id)
                for block in page_blocks:
                    merged_blocks.append(OcrTextBlock(text=block.text, bbox=block.bbox, conf=block.conf, page=page_index))
            return _build_record(
                merged_blocks,
                source_hash,
                retry_key,
                record_source_name,
                trace_id,
                settings,
                template_id,
                parser_version=f"ocr:{engine.__class__.__name__}",
                debug_info=debug_info,
            )
        finally:
            for image_path in image_paths:
                try:
                    os.remove(image_path)
                except OSError:
                    pass

    blocks = engine.extract_blocks(file_path, trace_id=trace_id)
    engine_warnings = engine.get_warnings()
    return _build_record(
        blocks,
        source_hash,
        retry_key,
        record_source_name,
        trace_id,
        settings,
        template_id,
        parser_version=f"ocr:{engine.__class__.__name__}",
        warnings=engine_warnings or None,
        debug_info=debug_info,
    )


def parse_file(
    path: str | Path,
    config: AppSettings,
    ocr_engine: OcrEngine | None = None,
    source_file_name: str | None = None,
    template_id: str | None = None,
    allow_pdf: bool | None = None,
    debug_info: dict[str, object] | None = None,
) -> InvoiceRecord:
    trace_id = uuid.uuid4().hex
    return parse_path(
        path,
        trace_id=trace_id,
        settings=config,
        ocr_engine=ocr_engine,
        source_file_name=source_file_name,
        template_id=template_id,
        allow_pdf=allow_pdf,
        debug_info=debug_info,
    )


def parse_path_multi(
    path: str | Path,
    trace_id: str,
    settings: AppSettings,
    ocr_engine: OcrEngine | None = None,
    source_file_name: str | None = None,
    template_id: str | None = None,
    allow_pdf: bool | None = None,
    debug_info: dict[str, object] | None = None,
) -> list[InvoiceRecord]:
    file_path = Path(path)
    if not file_path.exists():
        raise InputError(ErrorCode.E1001, "Input file not found", trace_id, {"path": str(file_path)})

    if file_path.suffix.lower() != ".pdf" or settings.pdf_mode != "per_page" or allow_pdf is True:
        return [
            parse_path(
                file_path,
                trace_id,
                settings,
                ocr_engine=ocr_engine,
                source_file_name=source_file_name,
                template_id=template_id,
                allow_pdf=allow_pdf,
                debug_info=debug_info,
            )
        ]

    source_hash = sha256_file(file_path)
    retry_key = build_retry_key(file_path, source_hash)
    record_source_name = source_file_name or file_path.name
    engine = _select_engine(settings, trace_id, ocr_engine)

    image_paths = render_pdf_to_images(file_path, settings.max_pdf_pages, trace_id)
    try:
        records: list[InvoiceRecord] = []
        for page_index, image_path in enumerate(image_paths, start=1):
            page_blocks = [
                OcrTextBlock(text=b.text, bbox=b.bbox, conf=b.conf, page=page_index)
                for b in engine.extract_blocks(image_path, trace_id=trace_id)
            ]
            record = _build_record(
                page_blocks,
                source_hash,
                retry_key,
                record_source_name,
                trace_id,
                settings,
                template_id,
                parser_version=f"ocr:{engine.__class__.__name__}",
                debug_info=debug_info,
            )
            record.doc_id = f"{record.doc_id}-p{page_index}"
            records.append(record)
        return records
    finally:
        for image_path in image_paths:
            try:
                os.remove(image_path)
            except OSError:
                pass
