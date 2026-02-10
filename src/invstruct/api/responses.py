from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from invstruct.errors import ErrorCode, error_payload
from invstruct.utils.trace import new_trace_id


def api_error_response(
    code: ErrorCode,
    message: str,
    *,
    status_code: int = 400,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    trace_id = new_trace_id()
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, trace_id, details or {}),
    )


def download_file_response(
    file_path: Path,
    *,
    media_type: str,
    filename: str,
) -> FileResponse:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
        headers=headers,
        background=BackgroundTask(lambda p: Path(p).unlink(missing_ok=True), str(file_path)),
    )
