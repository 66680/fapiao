from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Iterator


def new_trace_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def stage_timer(stage: str, trace_id: str) -> Iterator[dict[str, str | int]]:
    start = time.perf_counter()
    payload: dict[str, str | int] = {"trace_id": trace_id, "stage": stage, "elapsed_ms": 0}
    try:
        yield payload
    finally:
        payload["elapsed_ms"] = int((time.perf_counter() - start) * 1000)

