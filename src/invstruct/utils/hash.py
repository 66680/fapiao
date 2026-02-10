from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_retry_key(path: str | Path, sha256: str | None = None) -> str:
    file_path = Path(path)
    digest = sha256 or sha256_file(file_path)
    stat = file_path.stat()
    size = stat.st_size
    mtime_epoch = int(stat.st_mtime)
    return f"{digest[:16]}:{size}:{mtime_epoch}"


def canonical_json_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
