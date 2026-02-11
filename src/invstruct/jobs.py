from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from invstruct.utils.time_compat import UTC


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_job_state(job_id: str, n_files: int = 0) -> dict[str, Any]:
    now = now_iso()
    return {
        "job_id": job_id,
        "status": "running",
        "created_at": now,
        "updated_at": now,
        "bytes": 0,
        "n_files": n_files,
        "records": [],
        "failures": [],
    }


def list_job_files(job_dir: str | Path) -> list[Path]:
    root = Path(job_dir)
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def load_job(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_job(path: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = now_iso()
    payload["bytes"] = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def cleanup_jobs(job_dir: str | Path, retention_days: int, keep_last: int, dry_run: bool = False) -> dict[str, Any]:
    paths = list_job_files(job_dir)
    jobs_with_time: list[tuple[datetime, Path, dict[str, Any]]] = []

    for path in paths:
        try:
            payload = load_job(path)
            updated_raw = payload.get("updated_at") or payload.get("created_at")
            updated_dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00")) if isinstance(updated_raw, str) else datetime.now(UTC)
            jobs_with_time.append((updated_dt, path, payload))
        except Exception:
            continue

    jobs_with_time.sort(key=lambda item: item[0], reverse=True)
    keep_set = {item[1] for item in jobs_with_time[:max(keep_last, 0)]}
    threshold = datetime.now(UTC) - timedelta(days=max(retention_days, 0))

    to_delete: list[Path] = []
    for updated_dt, path, payload in jobs_with_time:
        if path in keep_set:
            continue
        if payload.get("status") == "running":
            continue
        if updated_dt < threshold:
            to_delete.append(path)

    deleted = []
    for path in to_delete:
        if not dry_run:
            path.unlink(missing_ok=True)
        deleted.append(str(path))

    return {
        "job_dir": str(job_dir),
        "total": len(jobs_with_time),
        "deleted": len(deleted),
        "dry_run": dry_run,
        "deleted_paths": deleted,
    }

