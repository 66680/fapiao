from __future__ import annotations

import json
import logging
from typing import Any


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")


def log_event(logger: logging.Logger, trace_id: str, stage: str, elapsed_ms: int, **details: Any) -> None:
    payload = {
        "trace_id": trace_id,
        "stage": stage,
        "elapsed_ms": elapsed_ms,
        **details,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))

