from __future__ import annotations

import uuid
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from invstruct.api.models import BatchSubmitResponse, JobResultsResponse, JobStatusResponse
from invstruct.api.responses import api_error_response, download_file_response
from invstruct.anomalies.engine import attach_anomalies
from invstruct.config import load_settings
from invstruct.errors import ErrorCode, ErrorEnvelope
from invstruct.export_templates.loader import get_export_template
from invstruct.exporters.details_csv import write_details_csv
from invstruct.exporters.mapped_csv import write_mapped_csv
from invstruct.exporters.report_xlsx import write_report_xlsx
from invstruct.jobs import create_job_state, load_job, save_job
from invstruct.pipeline.runner import parse_path
from invstruct.schemas import InvoiceRecord
from invstruct.templates.loader import load_templates
from invstruct.utils.trace import new_trace_id

router = APIRouter(tags=["batch"])


def _job_dir() -> Path:
    settings = load_settings("configs/app.yaml")
    path = Path(settings.job_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_file(job_id: str) -> Path:
    return _job_dir() / f"{job_id}.json"


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


def _job_records(payload: dict[str, Any], settings) -> list[InvoiceRecord]:
    rows = payload.get("records") or []
    records = [_to_invoice_record(row) for row in rows if isinstance(row, dict)]
    templates = {item.template_id: item for item in load_templates(settings.template_dir)}
    return attach_anomalies(records, config=settings.anomalies, templates=templates)


def _run_job(job_id: str, temp_files: list[tuple[Path, str]], template_id: str | None) -> None:
    settings = load_settings("configs/app.yaml")
    path = _job_file(job_id)
    payload = load_job(path)

    for file_path, original_name in temp_files:
        trace_id = new_trace_id()
        try:
            record = parse_path(
                file_path,
                trace_id,
                settings=settings,
                source_file_name=original_name,
                template_id=template_id,
            )
            payload["records"].append(record.to_dict())
        except Exception as exc:  # noqa: BLE001
            payload["failures"].append({"file_name": original_name, "error": str(exc), "trace_id": trace_id})
        finally:
            file_path.unlink(missing_ok=True)

    payload["status"] = "finished"
    save_job(path, payload)


@router.post(
    "/v1/batch",
    response_model=BatchSubmitResponse,
    summary="Create batch parse job",
    description="Upload one or multiple files and run parse asynchronously or synchronously.",
    responses={400: {"model": ErrorEnvelope}},
)
async def batch_parse(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Files to parse"),
    template_id: str | None = None,
    sync: bool = False,
) -> BatchSubmitResponse:
    job_id = str(uuid.uuid4())
    temp_files: list[tuple[Path, str]] = []

    for upload in files:
        suffix = Path(upload.filename or "input.bin").suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await upload.read())
            temp_files.append((Path(tmp.name), upload.filename or Path(tmp.name).name))

    job_state = create_job_state(job_id, n_files=len(temp_files))
    save_job(_job_file(job_id), job_state)

    if sync:
        _run_job(job_id, temp_files, template_id)
        payload = load_job(_job_file(job_id))
        return {"job_id": job_id, "status": payload["status"]}

    background_tasks.add_task(_run_job, job_id, temp_files, template_id)
    return {"job_id": job_id, "status": "running"}


@router.get(
    "/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get batch job status",
    description="Return current status and metadata for a job.",
)
def get_job_status(job_id: str) -> JobStatusResponse:
    path = _job_file(job_id)
    if not path.exists():
        return {"job_id": job_id, "status": "not_found"}
    payload = load_job(path)
    return {
        "job_id": job_id,
        "status": payload.get("status", "unknown"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "n_files": payload.get("n_files", 0),
        "bytes": payload.get("bytes", 0),
    }


@router.get(
    "/v1/jobs/{job_id}/results",
    response_model=JobResultsResponse,
    summary="Get batch job results",
    description="Return parsed records and failures payload for a finished or running job.",
)
def get_job_results(job_id: str) -> JobResultsResponse:
    path = _job_file(job_id)
    if not path.exists():
        return {"job_id": job_id, "status": "not_found", "records": [], "failures": []}
    payload = load_job(path)
    return payload


@router.get(
    "/v1/jobs/{job_id}/export",
    response_model=None,
    summary="Download batch export artifact",
    description="Export job results as report_xlsx/details_csv/accounting_csv.",
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
def export_job_results(
    job_id: str,
    kind: str,
    template_id: str | None = None,
) -> FileResponse | JSONResponse:
    path = _job_file(job_id)
    if not path.exists():
        return api_error_response(ErrorCode.E1001, "Job not found", status_code=404, details={"job_id": job_id})

    payload = load_job(path)
    settings = load_settings("configs/app.yaml")
    records = _job_records(payload, settings)
    out_dir = _job_dir() / "_exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex

    if kind == "report_xlsx":
        file_path = out_dir / f"{job_id}_{token}_report.xlsx"
        write_report_xlsx(records, file_path)
        return download_file_response(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{job_id}_report.xlsx",
        )

    if kind == "details_csv":
        file_path = out_dir / f"{job_id}_{token}_details.csv"
        write_details_csv(records, file_path)
        return download_file_response(
            file_path,
            media_type="text/csv",
            filename=f"{job_id}_details.csv",
        )

    if kind == "accounting_csv":
        if not template_id:
            return api_error_response(
                ErrorCode.E1001,
                "template_id is required for accounting_csv",
                details={"kind": kind},
            )
        export_template = get_export_template(template_id, settings.export_template_dir)
        if export_template is None:
            return api_error_response(
                ErrorCode.E1001,
                f"export template not found: {template_id}",
                details={"template_id": template_id},
            )
        file_path = out_dir / f"{job_id}_{token}_accounting.csv"
        write_mapped_csv(records, file_path, export_template)
        return download_file_response(
            file_path,
            media_type="text/csv",
            filename=f"{job_id}_accounting.csv",
        )

    return api_error_response(
        ErrorCode.E1001,
        "unknown export kind",
        details={"kind": kind, "supported": ["report_xlsx", "details_csv", "accounting_csv"]},
    )
