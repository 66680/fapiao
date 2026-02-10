from __future__ import annotations

import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from invstruct.config import load_settings
from invstruct.api.models import HealthResponse, ParseResponse
from invstruct.api.routes_batch import router as batch_router
from invstruct.api.routes_export import router as export_router
from invstruct.errors import ErrorCode, ErrorEnvelope, InputError, InvstructError, error_payload
from invstruct.jobs import cleanup_jobs
from invstruct.logging import log_event
from invstruct.pipeline.runner import parse_file
from invstruct.utils.trace import new_trace_id, stage_timer

logger = logging.getLogger(__name__)


def startup_cleanup_jobs() -> None:
    settings = load_settings("configs/app.yaml")
    if not settings.job_cleanup_on_startup:
        return
    try:
        result = cleanup_jobs(
            settings.job_dir,
            retention_days=settings.job_retention_days,
            keep_last=settings.job_keep_last,
            dry_run=False,
        )
        logger.info("job-cleanup %s", result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("job-cleanup failed: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup_cleanup_jobs()
    yield


app = FastAPI(
    title="invstruct API",
    version="0.1.0",
    description="Offline-first invoice structuring API with template-aware extraction and export tooling.",
    lifespan=lifespan,
)
app.include_router(batch_router)
app.include_router(export_router)


@app.exception_handler(InvstructError)
async def invstruct_exception_handler(_, exc: InvstructError) -> JSONResponse:
    payload = error_payload(exc.code, exc.message, exc.trace_id, exc.details)
    return JSONResponse(status_code=400, content=payload)


@app.get(
    "/healthz",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
    description="Lightweight liveness endpoint for service/process monitoring.",
)
def healthz() -> HealthResponse:
    return {"status": "ok"}


@app.post(
    "/v1/parse",
    response_model=ParseResponse,
    tags=["parse"],
    summary="Parse single file",
    description="Parse one invoice/receipt image (or PDF when `allow_pdf=true`) into a structured record.",
    responses={400: {"model": ErrorEnvelope}},
)
async def parse(
    file: UploadFile = File(..., description="Single JPG/PNG/PDF file"),
    allow_pdf: bool = False,
) -> ParseResponse:
    trace_id = new_trace_id()
    if not file.filename:
        raise InputError(ErrorCode.E1001, "Missing filename", trace_id)

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".pdf"}:
        raise InputError(ErrorCode.E1001, "Unsupported file type", trace_id, {"filename": file.filename})
    if suffix == ".pdf" and not allow_pdf:
        raise InputError(
            ErrorCode.E3001,
            "PDF not supported yet",
            trace_id,
            {"filename": file.filename, "allow_pdf": False},
        )

    with stage_timer("api.parse.upload", trace_id) as timer:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)
    log_event(logger, trace_id, "api.parse.upload", int(timer["elapsed_ms"]))

    with stage_timer("api.parse.runner", trace_id) as timer:
        settings = load_settings("configs/app.yaml")
        record = parse_file(
            tmp_path,
            config=settings,
            source_file_name=file.filename,
            allow_pdf=allow_pdf,
        )
    log_event(logger, trace_id, "api.parse.runner", int(timer["elapsed_ms"]))
    return {"trace_id": trace_id, "record": record.to_dict()}
