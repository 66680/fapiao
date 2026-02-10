from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invstruct.ocr.base import OcrEngine, OcrTextBlock


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_blocks(raw_blocks: list[dict[str, Any]]) -> list[OcrTextBlock]:
    blocks: list[OcrTextBlock] = []
    for item in raw_blocks:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        bbox_raw = item.get("bbox")
        bbox = bbox_raw if isinstance(bbox_raw, list) else []
        line_text = item.get("line_text")
        blocks.append(
            OcrTextBlock(
                text=text,
                bbox=bbox,
                conf=_as_float(item.get("conf"), 0.9),
                page=max(1, _as_int(item.get("page"), 1)),
                line_id=item.get("line_id"),
                line_text=line_text if isinstance(line_text, str) else text,
            )
        )
    return blocks


def _load_blocks_json(path: Path) -> list[OcrTextBlock] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        raw_blocks = payload.get("blocks")
        if isinstance(raw_blocks, list):
            return _to_blocks(raw_blocks)
    if isinstance(payload, list):
        return _to_blocks(payload)
    return None


def _match_record_file_name(record: dict[str, Any], file_name: str) -> bool:
    candidates = [
        record.get("file_name"),
        record.get("filename"),
        record.get("file"),
        record.get("source_file"),
    ]
    for item in candidates:
        if not isinstance(item, str):
            continue
        if Path(item).name == file_name:
            return True
    return False


def _load_blocks_jsonl(path: Path, file_name: str) -> list[OcrTextBlock] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if not _match_record_file_name(payload, file_name):
            continue
        raw_blocks = payload.get("blocks")
        if not isinstance(raw_blocks, list):
            continue
        return _to_blocks(raw_blocks)
    return None


class FixturesOcrEngine(OcrEngine):
    def __init__(self, fixtures_dir: str | Path | None = None) -> None:
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else None
        self._warnings: list[dict[str, Any]] = []

    def get_warnings(self) -> list[dict[str, Any]]:
        return list(self._warnings)

    def _set_missing_warning(self, file_path: Path, searched: list[Path]) -> None:
        self._warnings = [
            {
                "code": "fixtures_missing",
                "reason": "fixtures missing",
                "file_name": file_path.name,
                "searched": [str(path) for path in searched],
            }
        ]

    def extract_blocks(
        self,
        file_path: str | Path,
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> list[OcrTextBlock]:
        _ = trace_id, kwargs
        path = Path(file_path)
        self._warnings = []

        search_dirs: list[Path] = []
        if self.fixtures_dir is not None:
            search_dirs.append(self.fixtures_dir)
        if path.parent not in search_dirs:
            search_dirs.append(path.parent)

        checked_files: list[Path] = []
        for directory in search_dirs:
            block_file = directory / f"{path.stem}.blocks.json"
            checked_files.append(block_file)
            if not block_file.exists():
                continue
            loaded = _load_blocks_json(block_file)
            if loaded is not None:
                return loaded

        for directory in search_dirs:
            map_file = directory / ".invstruct.blocks.jsonl"
            checked_files.append(map_file)
            if not map_file.exists():
                continue
            loaded = _load_blocks_jsonl(map_file, path.name)
            if loaded is not None:
                return loaded

        self._set_missing_warning(path, checked_files)
        return []
