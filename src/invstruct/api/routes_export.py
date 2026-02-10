from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from invstruct.api.models import ExportPreviewResponse, ExportTemplateListResponse
from invstruct.api.responses import api_error_response
from invstruct.config import load_settings
from invstruct.errors import ErrorCode, ErrorEnvelope
from invstruct.export_templates.loader import get_export_template, load_export_templates
from invstruct.export_templates.models import ExportTemplateSpec
from invstruct.exporters.preview import preview_mapped
from invstruct.jobs import load_job
from invstruct.schemas import InvoiceRecord

router = APIRouter(tags=["export"])


def _job_file(job_id: str) -> Path:
    settings = load_settings("configs/app.yaml")
    job_dir = Path(settings.job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir / f"{job_id}.json"


def _to_invoice_record(payload: dict[str, Any]) -> InvoiceRecord:
    source = payload.get("source") or {}
    patched = dict(payload)
    patched["doc_id"] = patched.get("doc_id") or str(uuid.uuid4())
    patched["doc_type"] = patched.get("doc_type") or "unknown"
    patched["currency"] = patched.get("currency") or "CNY"
    patched["source"] = {
        "file_name": source.get("file_name") or str(payload.get("doc_id") or ""),
        "sha256": source.get("sha256") or "",
        "trace_id": source.get("trace_id") or "",
    }
    return InvoiceRecord.model_validate(patched)


def _resolve_template(
    *,
    template_id: str | None,
    template_yaml: str | None,
) -> ExportTemplateSpec | JSONResponse:
    settings = load_settings("configs/app.yaml")
    if template_yaml and template_yaml.strip():
        try:
            payload = yaml.safe_load(template_yaml) or {}
            return ExportTemplateSpec.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            return api_error_response(ErrorCode.E1001, f"invalid template_yaml: {exc}")

    if template_id and template_id.strip():
        item = get_export_template(template_id, settings.export_template_dir)
        if item is None:
            return api_error_response(
                ErrorCode.E1001,
                f"export template not found: {template_id}",
                details={"template_id": template_id},
            )
        return item

    return api_error_response(ErrorCode.E1001, "template_id or template_yaml is required")


def _preview_records_from_upload(upload: UploadFile, limit: int) -> tuple[list[InvoiceRecord], bool, int]:
    capped = max(1, min(limit, 200))
    upload.file.seek(0)
    records: list[InvoiceRecord] = []
    invalid_rows = 0
    has_more = False
    for raw in upload.file:
        line = raw.decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        if len(records) >= capped:
            has_more = True
            break
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid_rows += 1
            continue
        if not isinstance(payload, dict):
            invalid_rows += 1
            continue
        records.append(_to_invoice_record(payload))
    return records, has_more, invalid_rows


@router.get(
    "/v1/export/templates",
    response_model=ExportTemplateListResponse,
    summary="List export templates",
    description="List available accounting export templates from configured template directory.",
)
def list_export_templates() -> ExportTemplateListResponse:
    settings = load_settings("configs/app.yaml")
    templates = load_export_templates(settings.export_template_dir)
    return {
        "templates": [
            {
                "template_id": item.template_id,
                "version": item.version,
                "description": item.description,
                "columns": len(item.columns),
            }
            for item in templates
        ]
    }


@router.post(
    "/v1/export/preview",
    response_model=ExportPreviewResponse,
    summary="Preview mapped export rows",
    description="Upload records.jsonl and preview mapped export rows using template_id or inline template_yaml.",
    responses={400: {"model": ErrorEnvelope}},
)
async def export_preview(
    records: UploadFile = File(..., description="records.jsonl file"),
    template_id: str | None = Form(None),
    template_yaml: str | None = Form(None),
    limit: int = 20,
) -> Any:
    template = _resolve_template(template_id=template_id, template_yaml=template_yaml)
    if isinstance(template, JSONResponse):
        return template

    parsed_rows, has_more, invalid_rows = _preview_records_from_upload(records, limit)
    payload = preview_mapped(parsed_rows, template, limit=limit)
    payload["template_id"] = template.template_id
    payload["stats"]["invalid_rows"] = invalid_rows
    payload["stats"]["has_more"] = has_more
    return payload


@router.get(
    "/v1/jobs/{job_id}/export/preview",
    response_model=ExportPreviewResponse,
    summary="Preview mapped export rows by job",
    description="Preview top-N mapped export rows from existing batch job records.",
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
def export_preview_by_job(
    job_id: str,
    template_id: str | None = None,
    template_yaml: str | None = None,
    limit: int = 20,
) -> Any:
    path = _job_file(job_id)
    if not path.exists():
        return api_error_response(ErrorCode.E1001, "Job not found", status_code=404, details={"job_id": job_id})

    template = _resolve_template(template_id=template_id, template_yaml=template_yaml)
    if isinstance(template, JSONResponse):
        return template

    payload = load_job(path)
    rows = payload.get("records") or []
    source_rows = [item for item in rows if isinstance(item, dict)]
    capped = max(1, min(limit, 200))
    preview_rows = [_to_invoice_record(item) for item in source_rows[:capped]]
    result = preview_mapped(preview_rows, template, limit=limit)
    result["job_id"] = job_id
    result["template_id"] = template.template_id
    result["stats"]["has_more"] = len(source_rows) > capped
    result["stats"]["total_records"] = len(source_rows)
    return result
