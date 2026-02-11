from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from invstruct.jobs import cleanup_jobs
from invstruct.utils.time_compat import UTC


def _write_job(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_cleanup_jobs_prunes_old_but_keeps_running_and_dry_run(tmp_path: Path) -> None:
    old_time = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    recent_time = datetime.now(UTC).isoformat()

    old_finished = tmp_path / "old_finished.json"
    old_running = tmp_path / "old_running.json"
    recent_finished = tmp_path / "recent_finished.json"

    _write_job(
        old_finished,
        {
            "job_id": "j1",
            "status": "finished",
            "created_at": old_time,
            "updated_at": old_time,
            "bytes": 10,
            "n_files": 1,
            "records": [],
            "failures": [],
        },
    )
    _write_job(
        old_running,
        {
            "job_id": "j2",
            "status": "running",
            "created_at": old_time,
            "updated_at": old_time,
            "bytes": 10,
            "n_files": 1,
            "records": [],
            "failures": [],
        },
    )
    _write_job(
        recent_finished,
        {
            "job_id": "j3",
            "status": "finished",
            "created_at": recent_time,
            "updated_at": recent_time,
            "bytes": 10,
            "n_files": 1,
            "records": [],
            "failures": [],
        },
    )

    dry = cleanup_jobs(tmp_path, retention_days=30, keep_last=1, dry_run=True)
    assert dry["deleted"] >= 0
    assert old_finished.exists()
    assert old_running.exists()

    real = cleanup_jobs(tmp_path, retention_days=30, keep_last=1, dry_run=False)
    assert real["deleted"] >= 1
    assert not old_finished.exists()
    assert old_running.exists()

