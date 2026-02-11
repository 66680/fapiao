from __future__ import annotations

from invstruct import jobs
from invstruct.utils import time_compat


def test_jobs_module_imports_with_utc_compat() -> None:
    assert callable(jobs.now_iso)


def test_utc_constant_is_timezone_like() -> None:
    offset = time_compat.UTC.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 0

