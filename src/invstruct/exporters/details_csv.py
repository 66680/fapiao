from __future__ import annotations

import csv
import json
from pathlib import Path

from invstruct.schemas import FieldProvenance, InvoiceRecord

DETAIL_FIELDS = [
    "merchant_name",
    "issue_date",
    "total_amount_gross",
    "subtotal_amount_net",
    "tax_amount",
    "tax_rate",
    "currency",
    "invoice_number",
    "merchant_tax_id",
    "template_id",
    "doc_type",
    "status",
    "error_code",
    "error_message",
]

DETAIL_COLUMNS = [
    "doc_id",
    "field_name",
    "field_value",
    "confidence",
    "page",
    "bbox",
    "extractor",
    "line_id",
    "line_text",
    "merchant",
    "issue_date",
    "total_amount_gross",
    "currency",
    "invoice_no",
    "tax_id",
    "status",
    "error_code",
    "error_message",
    "warnings_count",
    "warnings_json",
    "parser_version",
    "retry_key",
    "source_file",
    "sha256",
    "trace_id",
]


def _row(record: InvoiceRecord, field_name: str, field_value: object) -> dict[str, object]:
    provenance = record.provenance.get(field_name, FieldProvenance())
    warnings = record.warnings or []
    warnings_json = json.dumps(warnings, ensure_ascii=False) if warnings else ""
    if len(warnings_json) > 2048:
        warnings_json = warnings_json[:2048] + "...(truncated)"
    return {
        "doc_id": record.doc_id,
        "field_name": field_name,
        "field_value": field_value,
        "confidence": record.confidence.fields.get(field_name),
        "page": provenance.page,
        "bbox": json.dumps(provenance.bbox, ensure_ascii=False),
        "extractor": provenance.extractor,
        "line_id": provenance.line_id,
        "line_text": provenance.line_text,
        "merchant": record.merchant_name,
        "issue_date": record.issue_date.isoformat() if record.issue_date else None,
        "total_amount_gross": record.total_amount_gross,
        "currency": record.currency,
        "invoice_no": record.invoice_number,
        "tax_id": record.merchant_tax_id,
        "status": record.status,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "warnings_count": len(warnings),
        "warnings_json": warnings_json,
        "parser_version": record.parser_version,
        "retry_key": record.retry_key,
        "source_file": record.source.file_name,
        "sha256": record.source.sha256,
        "trace_id": record.source.trace_id,
    }


def write_details_csv(records: list[InvoiceRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        for record in records:
            for field_name in DETAIL_FIELDS:
                value = getattr(record, field_name, None)
                writer.writerow(_row(record, field_name, value))
