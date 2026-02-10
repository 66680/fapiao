from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invstruct.export.schema_version import EXPORT_SCHEMA_VERSION


def _find_dedup_profile(input_records_path: Path) -> str | None:
    report_path = input_records_path.with_name("merge_report.json")
    if not report_path.exists():
        return None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("dedup_profile")
    return value if isinstance(value, str) and value.strip() else None


def build_export_manifest(
    *,
    input_records_path: Path,
    row_count: int,
    columns: list[str],
    outputs: dict[str, str],
) -> dict[str, Any]:
    return {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "tool_version": "invstruct/0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_records_path": str(input_records_path),
        "row_count": row_count,
        "columns": columns,
        "dedup_profile": _find_dedup_profile(input_records_path),
        "notes": "CSV header comments can be disabled via --no-header-comments; XLSX includes _meta sheet.",
        "outputs": outputs,
    }


def write_export_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
