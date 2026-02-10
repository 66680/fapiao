from __future__ import annotations

import json
import uuid
import csv as csvlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import typer
import yaml

from invstruct.anomalies.engine import attach_anomalies
from invstruct.config import AppSettings, load_settings
from invstruct.export.columns import EXPORT_COLUMNS_V1
from invstruct.export.manifest import build_export_manifest, write_export_manifest
from invstruct.errors import ErrorCode, InvstructError, error_payload
from invstruct.export.schema_version import EXPORT_SCHEMA_VERSION
from invstruct.exporters.details_csv import write_details_csv
from invstruct.exporters.mapped_csv import resolve_source_value, write_mapped_csv
from invstruct.exporters.preview import preview_mapped
from invstruct.exporters.report_xlsx import write_report_xlsx
from invstruct.export_templates.loader import get_export_template, load_export_template, load_export_templates
from invstruct.export_templates.models import ExportTemplateSpec, TRANSFORM_WHITELIST
from invstruct.export_templates.wizard import write_wizard_bundle
from invstruct.ocr.base import OcrEngine, OcrTextBlock
from invstruct.ocr.fixtures import FixturesOcrEngine
from invstruct.ocr.mock import MockOcrEngine
from invstruct.ocr.paddle import PaddleOcrEngine
from invstruct.pdf.render import render_pdf_to_images
from invstruct.pipeline.runner import build_error_record, build_skipped_record, parse_file
from invstruct.schemas import InvoiceRecord
from invstruct.templates.loader import load_template, load_templates
from invstruct.templates.models import TemplateSpec
from invstruct.templates.registry import TemplateRegistry
from invstruct.utils.hash import build_retry_key, canonical_json_sha256, sha256_file
from invstruct.utils.trace import new_trace_id

app = typer.Typer(help="invstruct CLI")
contract_app = typer.Typer(help="Contract governance commands")
template_app = typer.Typer(help="Template helper commands")
template_refine_app = typer.Typer(help="Template refine commands")
app.add_typer(contract_app, name="contract")
app.add_typer(template_app, name="template")
template_app.add_typer(template_refine_app, name="refine")

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SUPPORTED_INPUT_SUFFIXES = SUPPORTED_IMAGE_SUFFIXES.union({".pdf"})


def _echo_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False))


def _error_exit(
    code: ErrorCode,
    message: str,
    *,
    trace_id: str | None = None,
    details: dict[str, Any] | None = None,
    exit_code: int = 1,
) -> None:
    _echo_json(error_payload(code, message, trace_id or new_trace_id(), details))
    raise typer.Exit(exit_code)


def _iter_input_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    files: list[Path] = []
    for path in sorted(input_path.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES:
            files.append(path)
    return files


def _load_records_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        return []

    records: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def _to_invoice_record(payload: dict[str, Any]) -> InvoiceRecord:
    source = payload.get("source") or {}
    patched = dict(payload)
    patched["doc_id"] = patched.get("doc_id") or str(uuid.uuid4())
    patched["doc_type"] = patched.get("doc_type") or "unknown"
    patched["currency"] = patched.get("currency") or "CNY"
    patched["source"] = {
        "file_name": source.get("file_name") or str(payload.get("doc_id") or ""),
        "sha256": source.get("sha256") or "",
        "trace_id": source.get("trace_id") or "",
    }
    raw_issue_date = patched.get("issue_date")
    if isinstance(raw_issue_date, str):
        try:
            date.fromisoformat(raw_issue_date)
        except ValueError:
            patched["issue_date"] = None
    raw_amount = patched.get("total_amount_gross")
    if isinstance(raw_amount, str):
        try:
            patched["total_amount_gross"] = float(raw_amount.replace(",", ""))
        except ValueError:
            patched["total_amount_gross"] = None
    return InvoiceRecord.model_validate(patched)


def _load_invoice_records(path: Path) -> list[InvoiceRecord]:
    rows = _load_records_file(path)
    records: list[InvoiceRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        records.append(_to_invoice_record(row))
    return records


def _parse_export_formats(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _build_anomaly_rows(records: list[InvoiceRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for anomaly in record.anomalies:
            rows.append(
                {
                    "doc_id": record.doc_id,
                    "source_file": record.source.file_name,
                    "trace_id": record.source.trace_id,
                    "sha256": record.source.sha256,
                    "code": anomaly.code,
                    "message": anomaly.message,
                    "severity": anomaly.severity,
                    "details": anomaly.details,
                }
            )
    return rows


def _write_summary_csv(records: list[InvoiceRecord], path: Path, *, write_header_comments: bool = True) -> None:
    columns = [
        "file_name",
        "merchant",
        "issue_date",
        "total_amount_gross",
        "currency",
        "invoice_number",
        "tax_number",
        "invoice_no",
        "tax_id",
        "trace_id",
        "sha256",
        "status",
        "error_code",
        "error_message",
        "warnings_count",
        "warnings_json",
        "parser_version",
        "retry_key",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if write_header_comments:
            generated_at = datetime.now(timezone.utc).isoformat()
            handle.write(f"# invstruct_export_schema_version={EXPORT_SCHEMA_VERSION}\n")
            handle.write(f"# generated_at={generated_at}\n")
            handle.write("# tool_version=invstruct/0.1.0\n")
        writer = csvlib.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            warnings_count, warnings_json = _warnings_payload(record.warnings)
            writer.writerow(
                {
                    "file_name": record.source.file_name,
                    "merchant": record.merchant_name,
                    "issue_date": record.issue_date.isoformat() if record.issue_date else None,
                    "total_amount_gross": record.total_amount_gross,
                    "currency": record.currency,
                    "invoice_number": record.invoice_number,
                    "tax_number": record.merchant_tax_id,
                    "invoice_no": record.invoice_number,
                    "tax_id": record.merchant_tax_id,
                    "trace_id": record.source.trace_id,
                    "sha256": record.source.sha256,
                    "status": record.status,
                    "error_code": record.error_code,
                    "error_message": record.error_message,
                    "warnings_count": warnings_count,
                    "warnings_json": warnings_json,
                    "parser_version": record.parser_version,
                    "retry_key": record.retry_key,
                }
            )


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    path.write_text(content, encoding="utf-8")


def _status_rank(status: str | None) -> int:
    mapping = {"success": 3, "skipped": 2, "failed": 1}
    return mapping.get((status or "").strip().lower(), 0)


def _record_confidence(record: dict[str, Any]) -> float:
    confidence = record.get("confidence")
    if not isinstance(confidence, dict):
        return 0.0
    value = confidence.get("overall")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalized_merchant(record: dict[str, Any]) -> str:
    from invstruct.extractors.rules import normalize_for_rules

    value = record.get("merchant_name")
    if not isinstance(value, str):
        return ""
    return normalize_for_rules(value).strip().lower()


def _business_key(record: dict[str, Any]) -> str | None:
    merchant = _normalized_merchant(record)
    issue_date = str(record.get("issue_date") or "").strip()
    amount = str(record.get("total_amount_gross") or "").strip()
    currency = str(record.get("currency") or "").strip().upper()
    if not (merchant and issue_date and amount and currency):
        return None
    return f"{merchant}|{issue_date}|{amount}|{currency}"


def _retry_mtime_bucket(record: dict[str, Any], bucket_seconds: int = 86400) -> str | None:
    retry_key = record.get("retry_key")
    if not isinstance(retry_key, str) or not retry_key.strip():
        return None
    parts = retry_key.split(":")
    if len(parts) < 3:
        return None
    try:
        epoch = int(parts[2])
    except ValueError:
        return None
    return str(epoch // max(1, bucket_seconds))


def _merge_key_with_profile(record: dict[str, Any], profile: str) -> tuple[str, str]:
    profile_name = profile.strip().lower()
    source = record.get("source")
    source_sha = None
    source_file = ""
    if isinstance(source, dict):
        raw_sha = source.get("sha256")
        if isinstance(raw_sha, str) and raw_sha.strip():
            source_sha = raw_sha.strip()
        source_file = str(source.get("file_name") or "")

    if source_sha:
        return f"sha256:{source_sha}", "sha256"

    if profile_name == "strict_sha256":
        retry_key = record.get("retry_key")
        if isinstance(retry_key, str) and retry_key.strip():
            return f"retry_key:{retry_key.strip()}", "retry_key"
        doc_id = record.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            return f"doc_id:{doc_id.strip()}", "doc_id"
        return f"fallback:{canonical_json_sha256(record)}", "fallback"

    if profile_name == "business_key_hybrid":
        business = _business_key(record)
        if business:
            return f"business:{business}", "business_key"
        retry_key = record.get("retry_key")
        if isinstance(retry_key, str) and retry_key.strip():
            return f"retry_key:{retry_key.strip()}", "retry_key"
        doc_id = record.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            return f"doc_id:{doc_id.strip()}", "doc_id"
        return f"fallback:{canonical_json_sha256(record)}", "fallback"

    if profile_name == "temporal_window":
        bucket = _retry_mtime_bucket(record)
        if source_file and bucket:
            return f"temporal:{source_file}:{bucket}", "temporal_window"
        business = _business_key(record)
        if business:
            return f"business:{business}", "business_key_fallback"
        retry_key = record.get("retry_key")
        if isinstance(retry_key, str) and retry_key.strip():
            return f"retry_key:{retry_key.strip()}", "retry_key"
        doc_id = record.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            return f"doc_id:{doc_id.strip()}", "doc_id"
        return f"fallback:{canonical_json_sha256(record)}", "fallback"

    _error_exit(
        ErrorCode.E1001,
        f"Unsupported dedup profile: {profile_name}",
        details={"supported": ["strict_sha256", "business_key_hybrid", "temporal_window"]},
    )
    return "fallback:unsupported", "fallback"


def _choose_better_record(current: dict[str, Any], candidate: dict[str, Any]) -> tuple[dict[str, Any], str]:
    cur_rank = _status_rank(current.get("status"))
    new_rank = _status_rank(candidate.get("status"))
    if new_rank > cur_rank:
        return candidate, "status_priority"
    if new_rank < cur_rank:
        return current, "status_priority"
    cur_conf = _record_confidence(current)
    new_conf = _record_confidence(candidate)
    if new_conf > cur_conf:
        return candidate, "higher_confidence"
    if new_conf < cur_conf:
        return current, "higher_confidence"
    cur_id = str(current.get("doc_id", ""))
    new_id = str(candidate.get("doc_id", ""))
    if new_id and cur_id and new_id < cur_id:
        return candidate, "stable_tiebreak"
    return current, "stable_tiebreak"


def _parse_export_root_args(args: list[str]) -> tuple[Path | None, Path | None, Path | None, str, bool]:
    source_path: Path | None = None
    csv_path: Path | None = None
    xlsx_path: Path | None = None
    config_path = "configs/app.yaml"
    no_header_comments = False
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "--in":
            if idx + 1 >= len(args):
                _error_exit(ErrorCode.E1001, "Missing value for --in")
            source_path = Path(args[idx + 1])
            idx += 2
            continue
        if token == "--csv":
            if idx + 1 >= len(args):
                _error_exit(ErrorCode.E1001, "Missing value for --csv")
            csv_path = Path(args[idx + 1])
            idx += 2
            continue
        if token == "--xlsx":
            if idx + 1 >= len(args):
                _error_exit(ErrorCode.E1001, "Missing value for --xlsx")
            xlsx_path = Path(args[idx + 1])
            idx += 2
            continue
        if token == "--config":
            if idx + 1 >= len(args):
                _error_exit(ErrorCode.E1001, "Missing value for --config")
            config_path = args[idx + 1]
            idx += 2
            continue
        if token == "--no-header-comments":
            no_header_comments = True
            idx += 1
            continue
        if token.startswith("-"):
            _error_exit(ErrorCode.E1001, f"Unknown option for export root command: {token}")
        if source_path is None:
            source_path = Path(token)
        else:
            _error_exit(ErrorCode.E1001, f"Unexpected extra argument: {token}")
        idx += 1
    return source_path, csv_path, xlsx_path, config_path, no_header_comments


def _warnings_payload(raw: Any) -> tuple[int, str | None]:
    warnings = raw if isinstance(raw, list) else []
    count = len(warnings)
    if not warnings:
        return 0, None
    data = json.dumps(warnings, ensure_ascii=False)
    if len(data) > 2048:
        data = data[:2048] + "...(truncated)"
    return count, data


def _record_summary(file_name: str, record: dict[str, Any]) -> dict[str, Any]:
    source = record.get("source") or {}
    warnings_count, _ = _warnings_payload(record.get("warnings"))
    return {
        "file": file_name,
        "status": record.get("status", "success"),
        "error_code": record.get("error_code"),
        "warnings_count": warnings_count,
        "trace_id": source.get("trace_id"),
        "retry_key": record.get("retry_key"),
    }


def _write_debug_artifact(
    out_dir: Path,
    *,
    trace_id: str,
    source_file: str,
    debug_payload: dict[str, Any] | None,
    status: str,
    error: dict[str, Any] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "trace_id": trace_id,
        "source_file": source_file,
        "status": status,
        "rules": debug_payload or {},
    }
    if error:
        payload["error"] = error
    artifact_path = out_dir / f"debug_{trace_id}.json"
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_engine(
    settings: AppSettings,
    trace_id: str,
    engine_name: str | None = None,
    fixtures_dir: Path | None = None,
) -> OcrEngine:
    selected = (engine_name or "auto").strip().lower()
    if selected == "auto":
        selected = settings.ocr_engine.strip().lower()
    if selected == "fixtures":
        return FixturesOcrEngine(fixtures_dir=fixtures_dir)
    if selected == "paddle":
        return PaddleOcrEngine(trace_id=trace_id)
    if selected == "mock":
        return MockOcrEngine()
    raise ValueError(f"Unsupported ocr_engine: {selected}")


def _normalize_bbox(bbox: list[float], width: float, height: float) -> list[float]:
    if len(bbox) != 4 or width <= 0 or height <= 0:
        return [0.0, 0.0, 0.0, 0.0]
    x1, y1, x2, y2 = bbox
    return [round(x1 / width, 6), round(y1 / height, 6), round(x2 / width, 6), round(y2 / height, 6)]


def _resolve_template_reference(template_ref: str | None, settings: AppSettings) -> TemplateSpec | None:
    if not template_ref:
        return None
    path = Path(template_ref)
    if path.exists():
        return load_template(path)
    registry = TemplateRegistry(load_templates(settings.template_dir))
    return registry.get(template_ref)


def _load_template_overrides(settings: AppSettings) -> dict[str, TemplateSpec]:
    return {spec.template_id: spec for spec in load_templates(settings.template_dir)}


def _resolve_export_template(template_ref: str, settings: AppSettings) -> ExportTemplateSpec:
    template = get_export_template(template_ref, settings.export_template_dir)
    if template is None:
        available = [item.template_id for item in load_export_templates(settings.export_template_dir)]
        message = (
            f"Export template not found: {template_ref}. "
            f"Run `invstruct export templates list` to inspect available templates."
        )
        _error_exit(
            ErrorCode.E1001,
            message,
            details={"template": template_ref, "available_templates": available},
        )
    return template


def _merge_export_template_payload(
    base: ExportTemplateSpec,
    update_payload: dict[str, Any],
) -> ExportTemplateSpec:
    merged = base.model_dump(mode="python")
    if "template_id" in update_payload:
        merged["template_id"] = update_payload["template_id"]
    if "version" in update_payload:
        merged["version"] = update_payload["version"]
    if "description" in update_payload:
        merged["description"] = update_payload["description"]
    if "columns" in update_payload and isinstance(update_payload["columns"], list):
        merged["columns"] = update_payload["columns"]
    return ExportTemplateSpec.model_validate(merged)


def _build_export_refine_report(
    *,
    template: ExportTemplateSpec,
    records: list[InvoiceRecord],
    out_path: Path,
) -> dict[str, Any]:
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    rows = [record.to_dict() for record in records]
    preview_payload = preview_mapped(rows, template, limit=len(rows))
    preview_stats = preview_payload.get("stats", {})
    fallback_usage_by_column = preview_stats.get("fallback_usage_by_column", {})
    missing_required = 0
    for payload in rows:
        for column in template.columns:
            if not column.required:
                continue
            raw_value, _, _ = resolve_source_value(payload, column)
            if _is_missing(raw_value):
                missing_required += 1

    report = {
        "template_id": template.template_id,
        "rows": len(rows),
        "columns": len(template.columns),
        "missing_required_values": missing_required,
        "fallback_usage_by_column": fallback_usage_by_column,
        "source_usage_by_column": preview_stats.get("source_usage_by_column", {}),
        "transforms": list(TRANSFORM_WHITELIST),
        "output": str(out_path),
    }
    return report


def _collect_blocks(
    input_path: Path,
    settings: AppSettings,
    trace_id: str,
    engine_name: str | None,
    pdf_mode: str | None,
    fixtures_dir: Path | None = None,
) -> list[OcrTextBlock]:
    active_pdf_mode = (pdf_mode or settings.pdf_mode).strip().lower()
    engine = _pick_engine(settings, trace_id, engine_name, fixtures_dir=fixtures_dir)
    if input_path.suffix.lower() != ".pdf":
        return engine.extract_blocks(input_path, trace_id=trace_id)

    image_paths = render_pdf_to_images(input_path, settings.max_pdf_pages, trace_id)
    try:
        merged: list[OcrTextBlock] = []
        for page_index, image_path in enumerate(image_paths, start=1):
            page_blocks = engine.extract_blocks(image_path, trace_id=trace_id)
            if active_pdf_mode == "per_page":
                merged.extend(
                    OcrTextBlock(text=b.text, bbox=b.bbox, conf=b.conf, page=page_index)
                    for b in page_blocks
                )
            else:
                merged.extend(
                    OcrTextBlock(text=b.text, bbox=b.bbox, conf=b.conf, page=1)
                    for b in page_blocks
                )
        return merged
    finally:
        for image_path in image_paths:
            image_path.unlink(missing_ok=True)


def _editor_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>invstruct template editor</title>
  <style>
    body { margin: 0; font-family: sans-serif; display: grid; grid-template-columns: 280px 1fr; height: 100vh; }
    aside { padding: 12px; border-right: 1px solid #ddd; overflow: auto; }
    main { padding: 12px; overflow: auto; }
    svg { border: 1px solid #ddd; background: #fafafa; cursor: crosshair; touch-action: none; }
    .block { fill: rgba(0, 110, 255, .16); stroke: #2b67c6; stroke-width: 1; }
    .anchor { fill: rgba(255, 130, 0, .16); stroke: #ff7a00; stroke-width: 2; }
    .drag { fill: rgba(90, 40, 255, .15); stroke: #5a28ff; stroke-width: 2; stroke-dasharray: 4 2; pointer-events: none; }
    .hud-bg { fill: rgba(0, 0, 0, .72); }
    .hud-text { fill: #fff; font-size: 12px; font-family: monospace; }
    .row { margin-bottom: 8px; }
    label { display: block; margin-bottom: 4px; }
    input, select { width: 100%; }
    button { margin-right: 6px; margin-top: 4px; }
    pre { white-space: pre-wrap; word-break: break-word; font-size: 12px; }
    .overlay {
      position: fixed; right: 20px; top: 20px; z-index: 10;
      background: rgba(0, 0, 0, .86); color: #fff; padding: 12px 14px;
      border-radius: 6px; width: 320px; font-size: 13px; line-height: 1.4;
      box-shadow: 0 8px 24px rgba(0,0,0,.28);
    }
    .overlay.hidden { display: none; }
    .overlay h4 { margin: 0 0 8px; }
    .overlay code { background: rgba(255,255,255,.12); padding: 1px 4px; border-radius: 3px; }
  </style>
</head>
<body>
  <aside>
    <h3>Template Refinement</h3>
    <div class="row"><label>Field</label><select id="field"></select></div>
    <div class="row"><label>Direction</label>
      <select id="direction">
        <option value="right">right</option>
        <option value="below">below</option>
        <option value="right_or_below">right_or_below</option>
      </select>
    </div>
    <div class="row"><label>ROI (x1,y1,x2,y2 normalized)</label><input id="roi" value="0,0,1,1" /></div>
    <div class="row"><button id="save">Save Anchor</button></div>
    <div class="row">
      <button id="download-update">Download template_update.json</button>
      <button id="download-report">Download refine_report.json</button>
      <button id="toggle-hotkeys">Hotkeys</button>
    </div>
    <pre id="log"></pre>
  </aside>
  <main>
    <div class="row"><label>Page</label><select id="page"></select></div>
    <svg id="canvas" width="1000" height="700" viewBox="0 0 1000 700">
      <rect id="dragRect" class="drag" x="0" y="0" width="0" height="0" visibility="hidden"></rect>
      <g id="coordHUD" visibility="hidden">
        <rect id="coordHUDBG" class="hud-bg" x="760" y="10" width="230" height="44" rx="4" ry="4"></rect>
        <text id="coordHUDText" class="hud-text" x="770" y="28">x1=0 y1=0 x2=0 y2=0</text>
        <text id="coordHUDArea" class="hud-text" x="770" y="44">area=0</text>
      </g>
    </svg>
  </main>
  <div id="hotkeysOverlay" class="overlay hidden" role="dialog" aria-label="Hotkeys">
    <h4>Editor Hotkeys</h4>
    <div><code>Shift + Drag</code> Draw ROI (live rectangle + HUD)</div>
    <div><code>Arrow</code> Move ROI</div>
    <div><code>Ctrl + Arrow</code> Resize x2 / y2</div>
    <div><code>Ctrl + Shift + Arrow</code> Resize x1 / y1</div>
    <div><code>Alt</code> Fine step (0.001), <code>Shift</code> coarse step (0.02)</div>
    <div><code>Ctrl + Z</code> Undo</div>
    <div><code>Ctrl + Y</code> Redo</div>
    <div><code>Ctrl + Shift + Z</code> Redo</div>
    <div><code>?</code> or <code>H</code> Toggle this help</div>
    <div><code>Esc</code> Cancel active drag</div>
  </div>
  <script>
    const state = {
      blocks: [],
      pages: [],
      template: {},
      anchors: {},
      dragging: false,
      dragStart: null,
      dragCurrent: null,
      dragSuppressClick: false,
      minArea: 0.0005,
      minSpan: 0.0225,
      historyStack: [],
      historyIndex: -1,
      hotkeysVisible: false,
      suppressHistory: false
    };
    const fieldEl = document.getElementById("field");
    const pageEl = document.getElementById("page");
    const roiEl = document.getElementById("roi");
    const directionEl = document.getElementById("direction");
    const canvas = document.getElementById("canvas");
    const logEl = document.getElementById("log");
    const dragRect = document.getElementById("dragRect");
    const coordHUD = document.getElementById("coordHUD");
    const coordHUDText = document.getElementById("coordHUDText");
    const coordHUDArea = document.getElementById("coordHUDArea");
    const hotkeysOverlay = document.getElementById("hotkeysOverlay");
    const WIDTH = 1000;
    const HEIGHT = 700;

    function clamp(v){ return Math.max(0, Math.min(1, v)); }
    function toFixed4(v){ return Number(v).toFixed(4); }
    function deepClone(v){ return JSON.parse(JSON.stringify(v)); }
    function isTextInputFocused() {
      const active = document.activeElement;
      if (!active) return false;
      const tag = String(active.tagName || "").toLowerCase();
      return tag === "input" || tag === "textarea";
    }
    function saveFile(name, obj) {
      const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = name; a.click();
    }
    function roiArea(roi) {
      return Math.max(0, (roi[2] - roi[0]) * (roi[3] - roi[1]));
    }
    function roiFromPoints(a, b) {
      return [clamp(Math.min(a.x, b.x)), clamp(Math.min(a.y, b.y)), clamp(Math.max(a.x, b.x)), clamp(Math.max(a.y, b.y))];
    }
    function normalizeRoi(roi, edgeMode) {
      let [x1, y1, x2, y2] = roi.map(clamp);
      if (x1 > x2) { const t = x1; x1 = x2; x2 = t; }
      if (y1 > y2) { const t = y1; y1 = y2; y2 = t; }
      if (x2 - x1 < state.minSpan) {
        if (edgeMode === "x1") { x1 = clamp(x2 - state.minSpan); }
        else { x2 = clamp(x1 + state.minSpan); }
      }
      if (y2 - y1 < state.minSpan) {
        if (edgeMode === "y1") { y1 = clamp(y2 - state.minSpan); }
        else { y2 = clamp(y1 + state.minSpan); }
      }
      if (x2 - x1 < state.minSpan) {
        x1 = clamp(x2 - state.minSpan);
        x2 = clamp(x1 + state.minSpan);
      }
      if (y2 - y1 < state.minSpan) {
        y1 = clamp(y2 - state.minSpan);
        y2 = clamp(y1 + state.minSpan);
      }
      if (roiArea([x1, y1, x2, y2]) < state.minArea) {
        const side = Math.sqrt(state.minArea);
        if (x2 - x1 < side) {
          if (edgeMode === "x1") x1 = clamp(x2 - side);
          else x2 = clamp(x1 + side);
        }
        if (y2 - y1 < side) {
          if (edgeMode === "y1") y1 = clamp(y2 - side);
          else y2 = clamp(y1 + side);
        }
      }
      return [x1, y1, x2, y2].map(clamp);
    }
    function eventToNorm(evt) {
      const rect = canvas.getBoundingClientRect();
      const x = clamp((evt.clientX - rect.left) / rect.width);
      const y = clamp((evt.clientY - rect.top) / rect.height);
      return { x, y };
    }
    function setRoiInput(roi) {
      roiEl.value = [toFixed4(roi[0]), toFixed4(roi[1]), toFixed4(roi[2]), toFixed4(roi[3])].join(",");
    }
    function parseRoi() {
      const vals = roiEl.value.split(",").map(x => Number(x.trim()));
      if (vals.length !== 4 || vals.some(Number.isNaN)) return [0, 0, 1, 1];
      return vals.map(clamp);
    }
    function log(value){ logEl.textContent = value; }
    function currentField(){ return fieldEl.value; }
    function currentPage(){ return Number(pageEl.value || 1); }
    function updateCoordHUD(roi, visible) {
      if (!visible || !roi) {
        coordHUD.setAttribute("visibility", "hidden");
        return;
      }
      coordHUD.setAttribute("visibility", "visible");
      coordHUDText.textContent = `x1=${toFixed4(roi[0])} y1=${toFixed4(roi[1])} x2=${toFixed4(roi[2])} y2=${toFixed4(roi[3])}`;
      coordHUDArea.textContent = `area=${toFixed4(roiArea(roi))}`;
    }
    function ensureFieldAnchor(field) {
      if (!state.anchors[field]) {
        state.anchors[field] = { keywords: [], roi: [0,0,1,1], direction: directionEl.value || "right_or_below" };
      }
      return state.anchors[field];
    }
    function captureState() {
      return {
        anchors: deepClone(state.anchors),
        selectedField: currentField(),
        selectedPage: currentPage()
      };
    }
    function pushHistory(reason) {
      if (state.suppressHistory) return;
      const _ = reason;
      if (state.historyIndex < state.historyStack.length - 1) {
        state.historyStack = state.historyStack.slice(0, state.historyIndex + 1);
      }
      state.historyStack.push(captureState());
      state.historyIndex = state.historyStack.length - 1;
    }
    function applyState(snapshot) {
      if (!snapshot) return;
      state.suppressHistory = true;
      state.anchors = deepClone(snapshot.anchors || {});
      if (snapshot.selectedField && Array.from(fieldEl.options).some(op => op.value === snapshot.selectedField)) {
        fieldEl.value = snapshot.selectedField;
      }
      if (snapshot.selectedPage && Array.from(pageEl.options).some(op => Number(op.value) === Number(snapshot.selectedPage))) {
        pageEl.value = String(snapshot.selectedPage);
      }
      state.suppressHistory = false;
      syncFieldInputs();
      draw();
    }
    function undo() {
      if (state.historyIndex <= 0) return;
      state.historyIndex -= 1;
      applyState(state.historyStack[state.historyIndex]);
    }
    function redo() {
      if (state.historyIndex >= state.historyStack.length - 1) return;
      state.historyIndex += 1;
      applyState(state.historyStack[state.historyIndex]);
    }
    function setAnchorRoi(field, roi, edgeMode, reason) {
      const anchor = ensureFieldAnchor(field);
      anchor.roi = normalizeRoi(roi, edgeMode);
      setRoiInput(anchor.roi);
      updateCoordHUD(anchor.roi, true);
      log(JSON.stringify(anchor, null, 2));
      pushHistory(reason);
    }
    function syncFieldInputs() {
      const field = currentField();
      const anchor = state.anchors[field] || { roi: [0,0,1,1], direction: "right_or_below" };
      setRoiInput(anchor.roi || [0,0,1,1]);
      directionEl.value = anchor.direction || "right_or_below";
    }
    function toggleHotkeys() {
      state.hotkeysVisible = !state.hotkeysVisible;
      hotkeysOverlay.classList.toggle("hidden", !state.hotkeysVisible);
    }
    function updateDragOverlay(roi, visible) {
      if (!visible || !roi) {
        dragRect.setAttribute("visibility", "hidden");
        return;
      }
      dragRect.setAttribute("visibility", "visible");
      dragRect.setAttribute("x", String(roi[0] * WIDTH));
      dragRect.setAttribute("y", String(roi[1] * HEIGHT));
      dragRect.setAttribute("width", String(Math.max(1, (roi[2] - roi[0]) * WIDTH)));
      dragRect.setAttribute("height", String(Math.max(1, (roi[3] - roi[1]) * HEIGHT)));
      updateCoordHUD(roi, true);
    }
    function cancelDrag() {
      state.dragging = false;
      state.dragStart = null;
      state.dragCurrent = null;
      state.dragSuppressClick = false;
      updateDragOverlay(null, false);
    }
    function startDrag(evt) {
      if (!evt.shiftKey) return;
      const field = currentField();
      if (!field) return;
      state.dragging = true;
      state.dragStart = eventToNorm(evt);
      state.dragCurrent = state.dragStart;
      state.dragSuppressClick = true;
      setRoiInput([state.dragStart.x, state.dragStart.y, state.dragStart.x, state.dragStart.y]);
      updateDragOverlay([state.dragStart.x, state.dragStart.y, state.dragStart.x, state.dragStart.y], true);
      canvas.setPointerCapture(evt.pointerId);
      evt.preventDefault();
      evt.stopPropagation();
    }
    function updateDrag(evt) {
      if (!state.dragging || !state.dragStart) return;
      state.dragCurrent = eventToNorm(evt);
      const roi = roiFromPoints(state.dragStart, state.dragCurrent);
      setRoiInput(roi);
      updateDragOverlay(roi, true);
      evt.preventDefault();
      evt.stopPropagation();
    }
    function endDrag(evt) {
      if (!state.dragging || !state.dragStart) return;
      const field = currentField();
      state.dragCurrent = eventToNorm(evt);
      const roi = roiFromPoints(state.dragStart, state.dragCurrent);
      const area = roiArea(roi);
      if (field && area >= state.minArea) {
        const anchor = ensureFieldAnchor(field);
        anchor.roi = normalizeRoi(roi, null);
        anchor.direction = directionEl.value || anchor.direction || "right_or_below";
        setRoiInput(anchor.roi);
        log(JSON.stringify(anchor, null, 2));
        pushHistory("drag");
      }
      cancelDrag();
      draw();
      evt.preventDefault();
      evt.stopPropagation();
    }

    function draw() {
      for (const node of Array.from(canvas.querySelectorAll(".block,.anchor"))) {
        node.remove();
      }
      const page = currentPage();
      const width = WIDTH, height = HEIGHT;
      for (const block of state.blocks.filter(x => x.page === page)) {
        const [x1, y1, x2, y2] = block.bbox_norm || [0,0,0,0];
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", String(x1 * width));
        rect.setAttribute("y", String(y1 * height));
        rect.setAttribute("width", String(Math.max(1, (x2 - x1) * width)));
        rect.setAttribute("height", String(Math.max(1, (y2 - y1) * height)));
        rect.setAttribute("class", "block");
        rect.addEventListener("click", () => {
          if (state.dragSuppressClick) return;
          const field = currentField();
          if (!field) return;
          if (state.dragging) return;
          if (!state.anchors[field]) state.anchors[field] = { keywords: [], roi: [0,0,1,1], direction: "right_or_below" };
          const text = (block.text || "").trim();
          if (text && !state.anchors[field].keywords.includes(text)) {
            state.anchors[field].keywords.push(text);
            pushHistory("keyword");
          }
          log(JSON.stringify(state.anchors[field], null, 2));
        });
        canvas.appendChild(rect);
      }
      const field = currentField();
      const anchor = state.anchors[field];
      if (anchor && anchor.roi) {
        const [x1, y1, x2, y2] = anchor.roi;
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("x", String(x1 * width));
        rect.setAttribute("y", String(y1 * height));
        rect.setAttribute("width", String(Math.max(1, (x2 - x1) * width)));
        rect.setAttribute("height", String(Math.max(1, (y2 - y1) * height)));
        rect.setAttribute("class", "anchor");
        canvas.appendChild(rect);
        updateCoordHUD(anchor.roi, true);
      } else {
        updateCoordHUD(null, false);
      }
      if (state.dragging && state.dragStart && state.dragCurrent) {
        const roi = roiFromPoints(state.dragStart, state.dragCurrent);
        updateDragOverlay(roi, true);
      } else {
        updateDragOverlay(null, false);
      }
    }

    function handleArrowAction(evt) {
      const field = currentField();
      if (!field) return false;
      const anchor = ensureFieldAnchor(field);
      let [x1, y1, x2, y2] = anchor.roi || [0,0,1,1];
      const step = evt.altKey ? 0.001 : (evt.shiftKey ? 0.02 : 0.005);
      let edgeMode = null;
      if (evt.ctrlKey && evt.shiftKey) {
        if (evt.key === "ArrowLeft") { x1 -= step; edgeMode = "x1"; }
        if (evt.key === "ArrowRight") { x1 += step; edgeMode = "x1"; }
        if (evt.key === "ArrowUp") { y1 -= step; edgeMode = "y1"; }
        if (evt.key === "ArrowDown") { y1 += step; edgeMode = "y1"; }
      } else if (evt.ctrlKey) {
        if (evt.key === "ArrowLeft") { x2 -= step; edgeMode = "x2"; }
        if (evt.key === "ArrowRight") { x2 += step; edgeMode = "x2"; }
        if (evt.key === "ArrowUp") { y2 -= step; edgeMode = "y2"; }
        if (evt.key === "ArrowDown") { y2 += step; edgeMode = "y2"; }
      } else {
        if (evt.key === "ArrowLeft") { x1 -= step; x2 -= step; }
        if (evt.key === "ArrowRight") { x1 += step; x2 += step; }
        if (evt.key === "ArrowUp") { y1 -= step; y2 -= step; }
        if (evt.key === "ArrowDown") { y1 += step; y2 += step; }
      }
      setAnchorRoi(field, [x1, y1, x2, y2], edgeMode, "keyboard");
      draw();
      return true;
    }

    function handleKeydown(evt) {
      if (evt.key === "Escape") {
        cancelDrag();
        draw();
        return;
      }
      if (isTextInputFocused()) return;

      const lower = String(evt.key || "").toLowerCase();
      if (evt.key === "?" || lower === "h") {
        toggleHotkeys();
        evt.preventDefault();
        return;
      }
      if (evt.ctrlKey && lower === "z") {
        if (evt.shiftKey) redo();
        else undo();
        evt.preventDefault();
        return;
      }
      if (evt.ctrlKey && lower === "y") {
        redo();
        evt.preventDefault();
        return;
      }
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(evt.key)) {
        if (handleArrowAction(evt)) {
          evt.preventDefault();
        }
      }
    }

    function bindDrawing() {
      canvas.addEventListener("pointerdown", startDrag);
      canvas.addEventListener("pointermove", updateDrag);
      canvas.addEventListener("pointerup", endDrag);
      canvas.addEventListener("pointercancel", cancelDrag);
      document.addEventListener("keydown", handleKeydown);
      canvas.addEventListener("click", () => {
        if (state.dragSuppressClick) {
          state.dragSuppressClick = false;
        }
      }, true);
    }

    function initUi() {
      const aliases = state.template.aliases || {};
      const fields = Object.keys(aliases);
      fields.forEach((field) => {
        const op = document.createElement("option");
        op.value = field; op.textContent = field; fieldEl.appendChild(op);
      });
      const pages = (state.pages || []).map(p => p.page);
      pages.forEach((page) => {
        const op = document.createElement("option");
        op.value = String(page); op.textContent = `page ${page}`; pageEl.appendChild(op);
      });
      state.anchors = JSON.parse(JSON.stringify(state.template.anchors || {}));
      if (fields.length) fieldEl.value = fields[0];
      if (pages.length) pageEl.value = String(pages[0]);

      document.getElementById("save").onclick = () => {
        const field = currentField();
        if (!field) return;
        if (!state.anchors[field]) state.anchors[field] = { keywords: [], roi: [0,0,1,1], direction: "right_or_below" };
        state.anchors[field].roi = normalizeRoi(parseRoi(), null);
        state.anchors[field].direction = directionEl.value || "right_or_below";
        setRoiInput(state.anchors[field].roi);
        log(JSON.stringify(state.anchors[field], null, 2));
        pushHistory("save");
        draw();
      };
      document.getElementById("download-update").onclick = () => {
        saveFile("template_update.json", { anchors: state.anchors });
      };
      document.getElementById("download-report").onclick = () => {
        saveFile("refine_report.json", { updated_fields: Object.keys(state.anchors), generated_at: new Date().toISOString() });
      };
      document.getElementById("toggle-hotkeys").onclick = () => toggleHotkeys();
      roiEl.addEventListener("change", () => {
        const field = currentField();
        if (!field) return;
        const anchor = ensureFieldAnchor(field);
        anchor.roi = normalizeRoi(parseRoi(), null);
        setRoiInput(anchor.roi);
        log(JSON.stringify(anchor, null, 2));
        pushHistory("roi-input");
        draw();
      });
      directionEl.addEventListener("change", () => {
        const field = currentField();
        if (!field) return;
        const anchor = ensureFieldAnchor(field);
        anchor.direction = directionEl.value || "right_or_below";
        log(JSON.stringify(anchor, null, 2));
        pushHistory("direction");
      });
      fieldEl.onchange = () => {
        syncFieldInputs();
        draw();
      };
      pageEl.onchange = draw;
      bindDrawing();
      pushHistory("init");
      syncFieldInputs();
      draw();
    }

    async function boot() {
      try {
        const [blocksRes, pagesRes, templateRes] = await Promise.all([
          fetch("blocks.json"),
          fetch("pages.json"),
          fetch("template.json"),
        ]);
        const blocksPayload = await blocksRes.json();
        const pagesPayload = await pagesRes.json();
        state.template = await templateRes.json();
        state.blocks = blocksPayload.blocks || [];
        state.pages = pagesPayload.pages || [];
        initUi();
      } catch (error) {
        log(String(error));
      }
    }
    boot();
  </script>
</body>
</html>
"""


def _build_template_test_report(template_id: str, input_path: Path, out_dir: Path, settings: AppSettings) -> dict[str, Any]:
    trace_id = new_trace_id()
    record = parse_file(input_path, config=settings, source_file_name=input_path.name, template_id=template_id)
    required_fields = ["merchant_name", "issue_date", "total_amount_gross", "merchant_tax_id", "invoice_number"]
    missing = [field for field in required_fields if getattr(record, field) in {None, ""}]
    coverage = (len(required_fields) - len(missing)) / len(required_fields)
    top_candidates = {
        field: {"value": getattr(record, field), "confidence": record.confidence.fields.get(field)}
        for field in required_fields
    }
    report = {
        "template_id": template_id,
        "trace_id": trace_id,
        "coverage": coverage,
        "missing_fields": missing,
        "top_candidates": top_candidates,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "template_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


@app.command()
def parse(
    input_path: Path = typer.Argument(..., help="Input image path"),
    config: str = typer.Option("configs/app.yaml", "--config", help="App config yaml"),
    template_id: str | None = typer.Option(None, "--template-id"),
    allow_pdf: bool = typer.Option(False, "--allow-pdf", help="Enable PDF text parsing"),
    ocr_engine: str = typer.Option("auto", "--ocr-engine", help="OCR engine override: auto|mock|fixtures"),
    fixtures_dir: Path | None = typer.Option(None, "--fixtures-dir", help="Fixtures directory for fixtures engine"),
    debug_artifacts: bool = typer.Option(False, "--debug-artifacts", help="Write rules debug artifact"),
    out: Path = typer.Option(Path("out"), "--out", help="Debug artifact output directory"),
) -> None:
    if not input_path.exists():
        _error_exit(ErrorCode.E1001, "Input file not found", details={"path": str(input_path)})

    suffix = input_path.suffix.lower()
    if suffix == ".pdf" and not allow_pdf:
        _error_exit(
            ErrorCode.E3001,
            "PDF not supported yet",
            details={"path": str(input_path), "filename": input_path.name},
        )
    if suffix not in SUPPORTED_IMAGE_SUFFIXES and not (suffix == ".pdf" and allow_pdf):
        _error_exit(
            ErrorCode.E1001,
            "Unsupported file type",
            details={"path": str(input_path), "filename": input_path.name},
        )

    settings = load_settings(config)
    try:
        selected_engine = _pick_engine(
            settings,
            new_trace_id(),
            engine_name=ocr_engine,
            fixtures_dir=fixtures_dir,
        )
    except ValueError as exc:
        _error_exit(ErrorCode.E1001, str(exc), details={"ocr_engine": ocr_engine})

    debug_payload: dict[str, Any] | None = {} if debug_artifacts else None
    try:
        record = parse_file(
            input_path,
            config=settings,
            ocr_engine=selected_engine,
            source_file_name=input_path.name,
            template_id=template_id,
            allow_pdf=allow_pdf,
            debug_info=debug_payload,
        )
    except InvstructError as exc:
        if debug_artifacts:
            _write_debug_artifact(
                out,
                trace_id=exc.trace_id,
                source_file=input_path.name,
                debug_payload=debug_payload,
                status=str(exc.details.get("status", "failed")),
                error={"code": exc.code.value, "message": exc.message, "details": exc.details},
            )
        _error_exit(exc.code, exc.message, trace_id=exc.trace_id, details=exc.details)

    if debug_artifacts:
        _write_debug_artifact(
            out,
            trace_id=record.source.trace_id,
            source_file=record.source.file_name,
            debug_payload=debug_payload,
            status=record.status,
        )

    _echo_json(record.to_dict())


@app.command()
def batch(
    input_path: Path = typer.Argument(..., help="Input file or folder"),
    out: Path = typer.Option(Path("out"), "--out", help="Output directory"),
    config: str = typer.Option("configs/app.yaml", "--config", help="App config yaml"),
    template_id: str | None = typer.Option(None, "--template-id"),
    allow_pdf: bool = typer.Option(False, "--allow-pdf", help="Enable PDF text parsing"),
    ocr_engine: str = typer.Option("auto", "--ocr-engine", help="OCR engine override: auto|mock|fixtures"),
    fixtures_dir: Path | None = typer.Option(None, "--fixtures-dir", help="Fixtures directory for fixtures engine"),
    debug_artifacts: bool = typer.Option(False, "--debug-artifacts", help="Write per-file debug artifacts"),
    export_formats: str | None = typer.Option(None, "--export", help="Comma-separated export formats: xlsx,csv"),
    xlsx: Path | None = typer.Option(None, "--xlsx", help="Output xlsx path"),
    csv: Path | None = typer.Option(None, "--csv", help="Output csv path"),
) -> None:
    if not input_path.exists():
        _error_exit(ErrorCode.E1001, "Input path not found", details={"path": str(input_path)})

    settings = load_settings(config)
    try:
        selected_engine = _pick_engine(
            settings,
            new_trace_id(),
            engine_name=ocr_engine,
            fixtures_dir=fixtures_dir,
        )
    except ValueError as exc:
        _error_exit(ErrorCode.E1001, str(exc), details={"ocr_engine": ocr_engine})

    files = _iter_input_files(input_path)
    out.mkdir(parents=True, exist_ok=True)

    records: list[InvoiceRecord] = []
    failures: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    success_files = 0
    skipped_files = 0
    failed_files = 0

    for file_path in files:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            digest = sha256_file(file_path)
            retry_key = build_retry_key(file_path, digest)
            if not allow_pdf:
                trace_id = new_trace_id()
                skipped = build_skipped_record(
                    file_path,
                    trace_id=trace_id,
                    sha256=digest,
                    code=ErrorCode.E3001,
                    message="PDF not supported yet",
                    retry_key=retry_key,
                    parser_version="pdf-disabled",
                )
                records.append(skipped)
                if debug_artifacts:
                    _write_debug_artifact(
                        out,
                        trace_id=trace_id,
                        source_file=file_path.name,
                        debug_payload={},
                        status=skipped.status,
                        error={"code": skipped.error_code, "message": skipped.error_message},
                    )
                file_summaries.append(_record_summary(file_path.name, skipped.to_dict()))
                skipped_files += 1
                failures.append(
                    error_payload(
                        ErrorCode.E3001,
                        "PDF not supported yet",
                        trace_id,
                        {"path": str(file_path), "filename": file_path.name},
                    )
                )
                continue

            try:
                debug_payload: dict[str, Any] | None = {} if debug_artifacts else None
                record = parse_file(
                    file_path,
                    config=settings,
                    ocr_engine=selected_engine,
                    source_file_name=file_path.name,
                    template_id=template_id,
                    allow_pdf=True,
                    debug_info=debug_payload,
                )
                records.append(record)
                if debug_artifacts:
                    _write_debug_artifact(
                        out,
                        trace_id=record.source.trace_id,
                        source_file=file_path.name,
                        debug_payload=debug_payload,
                        status=record.status,
                    )
                file_summaries.append(_record_summary(file_path.name, record.to_dict()))
                success_files += 1
            except InvstructError as exc:
                status = str(exc.details.get("status", "skipped")).lower()
                parser_version = exc.details.get("parser_version")
                warnings_data = exc.details.get("warnings")
                if status == "failed":
                    error_record = build_error_record(
                        file_path,
                        trace_id=exc.trace_id,
                        sha256=digest,
                        status="failed",
                        code=exc.code,
                        message=exc.message,
                        retry_key=retry_key,
                        parser_version=parser_version,
                        warnings=warnings_data if isinstance(warnings_data, list) else None,
                    )
                    failed_files += 1
                else:
                    error_record = build_skipped_record(
                        file_path,
                        trace_id=exc.trace_id,
                        sha256=digest,
                        code=exc.code,
                        message=exc.message,
                        retry_key=retry_key,
                        parser_version=parser_version,
                        warnings=warnings_data if isinstance(warnings_data, list) else None,
                    )
                    skipped_files += 1
                records.append(error_record)
                if debug_artifacts:
                    _write_debug_artifact(
                        out,
                        trace_id=exc.trace_id,
                        source_file=file_path.name,
                        debug_payload={},
                        status=error_record.status,
                        error={"code": error_record.error_code, "message": error_record.error_message},
                    )
                file_summaries.append(_record_summary(file_path.name, error_record.to_dict()))
                failures.append(error_payload(exc.code, exc.message, exc.trace_id, exc.details))
            except Exception as exc:  # noqa: BLE001
                trace_id = new_trace_id()
                error_record = build_error_record(
                    file_path,
                    trace_id=trace_id,
                    sha256=digest,
                    status="failed",
                    code=ErrorCode.E3002,
                    message=str(exc),
                    retry_key=retry_key,
                )
                records.append(error_record)
                if debug_artifacts:
                    _write_debug_artifact(
                        out,
                        trace_id=trace_id,
                        source_file=file_path.name,
                        debug_payload={},
                        status=error_record.status,
                        error={"code": error_record.error_code, "message": error_record.error_message},
                    )
                file_summaries.append(_record_summary(file_path.name, error_record.to_dict()))
                failed_files += 1
                failures.append(
                    error_payload(
                        ErrorCode.E3002,
                        str(exc),
                        trace_id,
                        {"path": str(file_path), "filename": file_path.name, "status": "failed"},
                    )
                )
            continue

        try:
            debug_payload = {} if debug_artifacts else None
            record = parse_file(
                file_path,
                config=settings,
                ocr_engine=selected_engine,
                source_file_name=file_path.name,
                template_id=template_id,
                debug_info=debug_payload,
            )
            records.append(record)
            if debug_artifacts:
                _write_debug_artifact(
                    out,
                    trace_id=record.source.trace_id,
                    source_file=file_path.name,
                    debug_payload=debug_payload,
                    status=record.status,
                )
            file_summaries.append(_record_summary(file_path.name, record.to_dict()))
            success_files += 1
        except InvstructError as exc:
            failed_files += 1
            failures.append(error_payload(exc.code, exc.message, exc.trace_id, exc.details))
            file_summaries.append(
                {
                    "file": file_path.name,
                    "status": "failed",
                    "error_code": exc.code.value,
                    "warnings_count": 0,
                    "trace_id": exc.trace_id,
                    "retry_key": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            trace_id = new_trace_id()
            failed_files += 1
            failures.append(
                error_payload(
                    ErrorCode.E5001,
                    str(exc),
                    trace_id,
                    {"path": str(file_path), "filename": file_path.name},
                )
            )
            file_summaries.append(
                {
                    "file": file_path.name,
                    "status": "failed",
                    "error_code": ErrorCode.E5001.value,
                    "warnings_count": 0,
                    "trace_id": trace_id,
                    "retry_key": None,
                }
            )

    records = attach_anomalies(
        records,
        config=settings.anomalies,
        templates=_load_template_overrides(settings),
    )
    record_payloads = [record.to_dict() for record in records]
    records_path = out / "records.jsonl"
    failures_path = out / "failures.jsonl"
    report_path = out / "run_report.json"
    _append_jsonl(records_path, record_payloads)

    requested_formats = _parse_export_formats(export_formats)
    if xlsx:
        requested_formats.add("xlsx")
    if csv:
        requested_formats.add("csv")

    export_results: dict[str, dict[str, Any]] = {}
    if "xlsx" in requested_formats:
        xlsx_path = xlsx or (out / "report.xlsx")
        try:
            write_report_xlsx(records, xlsx_path)
            export_results["xlsx"] = {"status": "ok", "path": str(xlsx_path), "rows": len(records)}
        except Exception as exc:  # noqa: BLE001
            trace_id = new_trace_id()
            export_results["xlsx"] = {"status": "failed", "path": str(xlsx_path), "message": str(exc)}
            failures.append(error_payload(ErrorCode.E4001, f"xlsx export failed: {exc}", trace_id, {"path": str(xlsx_path)}))

    if "csv" in requested_formats:
        csv_path = csv or (out / "details.csv")
        try:
            write_details_csv(records, csv_path)
            export_results["csv"] = {"status": "ok", "path": str(csv_path), "rows": len(records)}
        except Exception as exc:  # noqa: BLE001
            trace_id = new_trace_id()
            export_results["csv"] = {"status": "failed", "path": str(csv_path), "message": str(exc)}
            failures.append(error_payload(ErrorCode.E4001, f"csv export failed: {exc}", trace_id, {"path": str(csv_path)}))

    _append_jsonl(failures_path, failures)

    report = {
        "input_path": str(input_path),
        "total_files": len(files),
        "summary": {
            "success": success_files,
            "skipped": skipped_files,
            "failed": failed_files,
        },
        "files": file_summaries,
        "success_files": success_files,
        "skipped_files": skipped_files,
        "failed_files": failed_files,
        "records_path": str(records_path),
        "failures_path": str(failures_path),
        "exports": export_results,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _echo_json(report)


def _parse_single_option(args: list[str], option: str, default: str | None = None) -> str | None:
    if option not in args:
        return default
    idx = args.index(option)
    if idx + 1 >= len(args):
        _error_exit(ErrorCode.E1001, f"Missing value for {option}")
    return args[idx + 1]


def _export_root(
    source_path: Path | None,
    csv: Path | None,
    xlsx: Path | None,
    config: str,
    *,
    no_header_comments: bool = False,
) -> None:
    if source_path is None:
        _error_exit(ErrorCode.E1001, "Missing input records file", details={"hint": "--in <records.jsonl>"})
    if not source_path.exists():
        _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(source_path)})

    settings = load_settings(config)
    records = _load_invoice_records(source_path)
    records = attach_anomalies(records, config=settings.anomalies, templates=_load_template_overrides(settings))

    if csv:
        _write_summary_csv(records, csv, write_header_comments=not no_header_comments)
    if xlsx:
        write_report_xlsx(records, xlsx)
    if not csv and not xlsx:
        _echo_json({"rows": len(records), "records_file": str(source_path)})
        return
    _echo_json({"rows": len(records), "csv": str(csv) if csv else None, "xlsx": str(xlsx) if xlsx else None})


def _export_list_compat(config: str) -> None:
    settings = load_settings(config)
    templates = load_export_templates(settings.export_template_dir)
    _echo_json(
        {
            "templates": [
                {
                    "template_id": item.template_id,
                    "version": item.version,
                    "description": item.description,
                    "columns": len(item.columns),
                }
                for item in templates
            ]
        }
    )


def _export_accounting(in_path: Path, template: str, out: Path, config: str) -> None:
    if not in_path.exists():
        _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(in_path)})
    settings = load_settings(config)
    export_template = _resolve_export_template(template, settings)
    records = _load_invoice_records(in_path)
    records = attach_anomalies(records, config=settings.anomalies, templates=_load_template_overrides(settings))
    write_mapped_csv(records, out, export_template)
    _echo_json({"rows": len(records), "template_id": export_template.template_id, "out": str(out)})


def _export_templates_list(config: str) -> None:
    settings = load_settings(config)
    templates = load_export_templates(settings.export_template_dir)
    _echo_json(
        {
            "templates": [
                {
                    "template_id": item.template_id,
                    "version": item.version,
                    "description": item.description,
                    "columns": len(item.columns),
                }
                for item in templates
            ]
        }
    )


def _export_templates_show(template: str, config: str) -> None:
    settings = load_settings(config)
    item = get_export_template(template, settings.export_template_dir)
    if item is None:
        _error_exit(
            ErrorCode.E1001,
            f"Export template not found: {template}",
            details={"template": template},
        )
    _echo_json(item.model_dump(mode="json"))


def _export_templates_validate(template_path: Path) -> None:
    item = load_export_template(template_path)
    _echo_json({"template_id": item.template_id, "valid": True})


def _export_templates_wizard(in_path: Path, base: str, out_dir: Path, rows: int, config: str) -> None:
    if not in_path.exists():
        _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(in_path)})
    settings = load_settings(config)
    records = _load_invoice_records(in_path)
    records = attach_anomalies(records, config=settings.anomalies, templates=_load_template_overrides(settings))
    base_template = _resolve_export_template(base, settings)
    report = write_wizard_bundle(records=records, base_template=base_template, out_dir=out_dir, preview_rows=rows)
    _echo_json({"out": str(out_dir), "report": report})


def _export_templates_refine_apply(base: str, update: Path, out: Path, config: str) -> None:
    if not update.exists():
        _error_exit(ErrorCode.E1001, "Update json not found", details={"path": str(update)})
    settings = load_settings(config)
    base_template = _resolve_export_template(base, settings)
    payload = json.loads(update.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        _error_exit(ErrorCode.E1001, "Invalid update payload", details={"path": str(update)})
    merged = _merge_export_template_payload(base_template, payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(merged.model_dump(mode="python"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    _ = load_export_template(out)
    _echo_json({"base": base, "update": str(update), "out": str(out), "valid": True})


def _export_templates_refine_test(
    template: str,
    in_path: Path,
    out: Path,
    report: Path,
    config: str,
) -> None:
    if not in_path.exists():
        _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(in_path)})
    settings = load_settings(config)
    template_spec = _resolve_export_template(template, settings)
    records = _load_invoice_records(in_path)
    records = attach_anomalies(records, config=settings.anomalies, templates=_load_template_overrides(settings))
    write_mapped_csv(records, out, template_spec)
    payload = _build_export_refine_report(template=template_spec, records=records, out_path=out)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _echo_json({"template_id": template_spec.template_id, "out": str(out), "report": str(report), "rows": len(records)})


def _column_sources(column: Any) -> list[str]:
    sources: list[str] = []
    source_candidates = getattr(column, "source_candidates", None) or []
    if source_candidates:
        sources = [item for item in source_candidates if item]
    elif getattr(column, "source", None):
        sources = [column.source]
    return sources


def _diff_export_templates(a_template: ExportTemplateSpec, b_template: ExportTemplateSpec) -> dict[str, Any]:
    a_columns = a_template.columns
    b_columns = b_template.columns
    pairs: list[tuple[int, int]] = []
    matched_a: set[int] = set()
    matched_b: set[int] = set()

    a_name_map: dict[str, list[int]] = {}
    b_name_map: dict[str, list[int]] = {}
    for idx, item in enumerate(a_columns):
        a_name_map.setdefault(item.name, []).append(idx)
    for idx, item in enumerate(b_columns):
        b_name_map.setdefault(item.name, []).append(idx)

    for name in sorted(set(a_name_map) & set(b_name_map)):
        a_indexes = a_name_map[name]
        b_indexes = b_name_map[name]
        if len(a_indexes) == 1 and len(b_indexes) == 1:
            a_idx = a_indexes[0]
            b_idx = b_indexes[0]
            pairs.append((a_idx, b_idx))
            matched_a.add(a_idx)
            matched_b.add(b_idx)

    remaining_a = [idx for idx in range(len(a_columns)) if idx not in matched_a]
    remaining_b = [idx for idx in range(len(b_columns)) if idx not in matched_b]
    for a_idx, b_idx in zip(remaining_a, remaining_b, strict=False):
        pairs.append((a_idx, b_idx))
        matched_a.add(a_idx)
        matched_b.add(b_idx)

    added = []
    removed = []
    moved = []
    modified = []

    for idx, column in enumerate(a_columns):
        if idx not in matched_a:
            removed.append({"name": column.name, "index": idx})
    for idx, column in enumerate(b_columns):
        if idx not in matched_b:
            added.append({"name": column.name, "index": idx})

    for a_idx, b_idx in pairs:
        a_col = a_columns[a_idx]
        b_col = b_columns[b_idx]
        if a_idx != b_idx:
            moved.append({"name": b_col.name, "from": a_idx, "to": b_idx})

        field_changes: dict[str, dict[str, Any]] = {}
        for key, left, right in [
            ("name", a_col.name, b_col.name),
            ("transform", a_col.transform, b_col.transform),
            ("required", a_col.required, b_col.required),
            ("default", a_col.default, b_col.default),
            ("sources", _column_sources(a_col), _column_sources(b_col)),
        ]:
            if left != right:
                field_changes[key] = {"from": left, "to": right}
        if field_changes:
            modified.append(
                {
                    "index_a": a_idx,
                    "index_b": b_idx,
                    "name_a": a_col.name,
                    "name_b": b_col.name,
                    "changes": field_changes,
                }
            )

    return {
        "template_a": a_template.template_id,
        "template_b": b_template.template_id,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "moved": len(moved),
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "moved": moved,
    }


def _render_export_diff_markdown(diff_payload: dict[str, Any]) -> str:
    def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
        content = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        for row in rows:
            content.append("| " + " | ".join(row) + " |")
        return content

    lines = ["# Export Template Diff Report", ""]
    lines.extend(
        _table(
            ["Key", "Value"],
            [
                ["Template A", str(diff_payload.get("template_a", ""))],
                ["Template B", str(diff_payload.get("template_b", ""))],
            ],
        )
    )
    summary = diff_payload.get("summary", {})
    lines.extend(["", "## Summary", ""])
    lines.extend(
        _table(
            ["Added", "Removed", "Modified", "Moved"],
            [[str(summary.get("added", 0)), str(summary.get("removed", 0)), str(summary.get("modified", 0)), str(summary.get("moved", 0))]],
        )
    )

    lines.extend(["", "## Added Columns", ""])
    added_rows = [[str(item.get("name", "")), str(item.get("index", ""))] for item in diff_payload.get("added", [])]
    lines.extend(_table(["Column", "Index"], added_rows or [["-", "-"]]))

    lines.extend(["", "## Removed Columns", ""])
    removed_rows = [[str(item.get("name", "")), str(item.get("index", ""))] for item in diff_payload.get("removed", [])]
    lines.extend(_table(["Column", "Index"], removed_rows or [["-", "-"]]))

    lines.extend(["", "## Modified Columns", ""])
    modified_rows = [
        [
            str(item.get("name_a", "")),
            str(item.get("index_a", "")),
            str(item.get("name_b", "")),
            str(item.get("index_b", "")),
            ", ".join(item.get("changes", {}).keys()),
        ]
        for item in diff_payload.get("modified", [])
    ]
    lines.extend(_table(["Name A", "Index A", "Name B", "Index B", "Changed Fields"], modified_rows or [["-", "-", "-", "-", "-"]]))

    lines.extend(["", "## Moved Columns", ""])
    moved_rows = [[str(item.get("name", "")), str(item.get("from", "")), str(item.get("to", ""))] for item in diff_payload.get("moved", [])]
    lines.extend(_table(["Column", "From", "To"], moved_rows or [["-", "-", "-"]]))
    lines.append("")
    return "\n".join(lines)


def _export_templates_diff(a: str, b: str, out: Path, fmt: str, config: str) -> None:
    settings = load_settings(config)
    template_a = _resolve_export_template(a, settings)
    template_b = _resolve_export_template(b, settings)
    formats = {item.strip().lower() for item in fmt.split(",") if item.strip()}
    if not formats:
        formats = {"json"}
    invalid = formats - {"json", "md"}
    if invalid:
        _error_exit(
            ErrorCode.E1001,
            "Invalid diff format",
            details={"format": fmt, "supported": ["json", "md"], "invalid": sorted(invalid)},
        )

    out.mkdir(parents=True, exist_ok=True)
    diff_payload = _diff_export_templates(template_a, template_b)
    outputs: dict[str, str] = {}
    if "json" in formats:
        json_path = out / "diff_report.json"
        json_path.write_text(json.dumps(diff_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs["json"] = str(json_path)
    if "md" in formats:
        md_path = out / "diff_report.md"
        md_path.write_text(_render_export_diff_markdown(diff_payload), encoding="utf-8")
        outputs["md"] = str(md_path)

    _echo_json({"out": str(out), "outputs": outputs, "summary": diff_payload["summary"]})


@app.command(
    "export",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def export_command(ctx: typer.Context) -> None:
    args = list(ctx.args)
    if not args:
        _error_exit(
            ErrorCode.E1001,
            "Missing export arguments",
            details={"hint": "export --in <records.jsonl> --xlsx <path> --csv <path>"},
        )

    if args[0] == "accounting":
        sub_args = args[1:]
        in_raw = _parse_single_option(sub_args, "--in")
        template = _parse_single_option(sub_args, "--template")
        out_raw = _parse_single_option(sub_args, "--out")
        config = _parse_single_option(sub_args, "--config", "configs/app.yaml") or "configs/app.yaml"
        if in_raw is None or template is None or out_raw is None:
            _error_exit(
                ErrorCode.E1001,
                "Missing required options for export accounting",
                details={"required": ["--in", "--template", "--out"]},
            )
        _export_accounting(Path(in_raw), template, Path(out_raw), config)
        return

    if args[0] == "list":
        config = _parse_single_option(args[1:], "--config", "configs/app.yaml") or "configs/app.yaml"
        _export_list_compat(config)
        return

    if args[0] == "templates":
        sub_args = args[1:]
        if not sub_args:
            _error_exit(
                ErrorCode.E1001,
                "Missing templates subcommand",
                details={"hint": "export templates list|show|validate|wizard|refine|diff"},
            )
        action = sub_args[0]
        if action == "list":
            config = _parse_single_option(sub_args[1:], "--config", "configs/app.yaml") or "configs/app.yaml"
            _export_templates_list(config)
            return
        if action == "show":
            if len(sub_args) < 2:
                _error_exit(ErrorCode.E1001, "Missing template id for export templates show")
            template = sub_args[1]
            config = _parse_single_option(sub_args[2:], "--config", "configs/app.yaml") or "configs/app.yaml"
            _export_templates_show(template, config)
            return
        if action == "validate":
            if len(sub_args) < 2:
                _error_exit(ErrorCode.E1001, "Missing template path for export templates validate")
            _export_templates_validate(Path(sub_args[1]))
            return
        if action == "wizard":
            in_raw = _parse_single_option(sub_args[1:], "--in")
            base = _parse_single_option(sub_args[1:], "--base")
            out_raw = _parse_single_option(sub_args[1:], "--out")
            rows_raw = _parse_single_option(sub_args[1:], "--rows", "20") or "20"
            config = _parse_single_option(sub_args[1:], "--config", "configs/app.yaml") or "configs/app.yaml"
            if in_raw is None or base is None or out_raw is None:
                _error_exit(
                    ErrorCode.E1001,
                    "Missing required options for export templates wizard",
                    details={"required": ["--in", "--base", "--out"]},
                )
            try:
                rows = int(rows_raw)
            except ValueError:
                _error_exit(ErrorCode.E1001, "Invalid --rows value", details={"rows": rows_raw})
                return
            _export_templates_wizard(Path(in_raw), base, Path(out_raw), rows, config)
            return
        if action == "refine":
            if len(sub_args) < 2:
                _error_exit(
                    ErrorCode.E1001,
                    "Missing refine action",
                    details={"hint": "export templates refine apply|test"},
                )
            refine_action = sub_args[1]
            refine_args = sub_args[2:]
            if refine_action == "apply":
                base = _parse_single_option(refine_args, "--base")
                update_raw = _parse_single_option(refine_args, "--update")
                out_raw = _parse_single_option(refine_args, "--out")
                config = _parse_single_option(refine_args, "--config", "configs/app.yaml") or "configs/app.yaml"
                if base is None or update_raw is None or out_raw is None:
                    _error_exit(
                        ErrorCode.E1001,
                        "Missing required options for export templates refine apply",
                        details={"required": ["--base", "--update", "--out"]},
                    )
                _export_templates_refine_apply(base, Path(update_raw), Path(out_raw), config)
                return
            if refine_action == "test":
                template = _parse_single_option(refine_args, "--template")
                in_raw = _parse_single_option(refine_args, "--in")
                out_raw = _parse_single_option(refine_args, "--out")
                report_raw = _parse_single_option(refine_args, "--report")
                config = _parse_single_option(refine_args, "--config", "configs/app.yaml") or "configs/app.yaml"
                if template is None or in_raw is None or out_raw is None or report_raw is None:
                    _error_exit(
                        ErrorCode.E1001,
                        "Missing required options for export templates refine test",
                        details={"required": ["--template", "--in", "--out", "--report"]},
                    )
                _export_templates_refine_test(template, Path(in_raw), Path(out_raw), Path(report_raw), config)
                return
            _error_exit(ErrorCode.E1001, f"Unsupported export templates refine action: {refine_action}")
            return
        if action == "diff":
            a_ref = _parse_single_option(sub_args[1:], "--a")
            b_ref = _parse_single_option(sub_args[1:], "--b")
            out_raw = _parse_single_option(sub_args[1:], "--out")
            fmt = _parse_single_option(sub_args[1:], "--format", "json") or "json"
            config = _parse_single_option(sub_args[1:], "--config", "configs/app.yaml") or "configs/app.yaml"
            if a_ref is None or b_ref is None or out_raw is None:
                _error_exit(
                    ErrorCode.E1001,
                    "Missing required options for export templates diff",
                    details={"required": ["--a", "--b", "--out"]},
                )
            _export_templates_diff(a_ref, b_ref, Path(out_raw), fmt, config)
            return
        _error_exit(ErrorCode.E1001, f"Unsupported export templates action: {action}")
        return

    source_path, csv, xlsx, config, no_header_comments = _parse_export_root_args(args)
    _export_root(source_path, csv, xlsx, config, no_header_comments=no_header_comments)


@app.command()
def merge(
    inputs: list[Path] = typer.Argument(..., help="Input records jsonl/json files"),
    out: Path = typer.Option(..., "--out", help="Merged output jsonl"),
    dedup_profile: str = typer.Option(
        "strict_sha256",
        "--dedup-profile",
        help="Dedup profile: strict_sha256|business_key_hybrid|temporal_window",
    ),
) -> None:
    merged_by_key: dict[str, dict[str, Any]] = {}
    key_type_by_key: dict[str, str] = {}
    dropped: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    reason_stats: dict[str, int] = {}
    key_type_stats: dict[str, int] = {}
    input_rows = 0

    for input_path in inputs:
        if not input_path.exists():
            _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(input_path)})
        for row in _load_records_file(input_path):
            if not isinstance(row, dict):
                continue
            input_rows += 1
            dedup_key, key_type = _merge_key_with_profile(row, dedup_profile)
            existing = merged_by_key.get(dedup_key)
            if existing is None:
                merged_by_key[dedup_key] = row
                key_type_by_key[dedup_key] = key_type
                key_type_stats[key_type] = key_type_stats.get(key_type, 0) + 1
                continue
            kept, reason = _choose_better_record(existing, row)
            dropped_row = row if kept is existing else existing
            merged_by_key[dedup_key] = kept
            reason_stats[reason] = reason_stats.get(reason, 0) + 1
            kept_hash = canonical_json_sha256(kept)
            dropped_hash = canonical_json_sha256(dropped_row)
            dropped.append(
                {
                    "key": dedup_key,
                    "key_type": key_type_by_key.get(dedup_key, key_type),
                    "reason": reason,
                    "kept_doc_id": str(kept.get("doc_id", "")),
                    "kept_snapshot_hash": kept_hash,
                    "dropped_doc_id": str(dropped_row.get("doc_id", "")),
                    "dropped_snapshot_hash": dropped_hash,
                    "kept_status": kept.get("status"),
                    "dropped_status": dropped_row.get("status"),
                }
            )
            conflicts.append(
                {
                    "key": dedup_key,
                    "key_type": key_type_by_key.get(dedup_key, key_type),
                    "kept_doc_id": str(kept.get("doc_id", "")),
                    "kept_snapshot_hash": kept_hash,
                    "dropped": [
                        {
                            "doc_id": str(dropped_row.get("doc_id", "")),
                            "snapshot_hash": dropped_hash,
                            "reason": reason,
                        }
                    ],
                }
            )

    def _sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
        source = item.get("source")
        file_name = ""
        sha256 = ""
        if isinstance(source, dict):
            file_name = str(source.get("file_name") or "")
            sha256 = str(source.get("sha256") or "")
        return (file_name, sha256, str(item.get("doc_id", "")))

    merged_rows = sorted(merged_by_key.values(), key=_sort_key)
    _append_jsonl(out, merged_rows)

    report_path = out.with_name("merge_report.json")
    report_payload = {
        "inputs": [str(path) for path in inputs],
        "dedup_profile": dedup_profile,
        "input_rows": input_rows,
        "kept_rows": len(merged_rows),
        "dropped_rows": len(dropped),
        "reason_stats": reason_stats,
        "key_type_stats": key_type_stats,
        "snapshot_hash_algorithm": "sha256(canonical_json)",
        "conflicts": conflicts,
        "dropped": dropped,
        "out": str(out),
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _echo_json(
        {
            "out": str(out),
            "merge_report": str(report_path),
            "input_rows": input_rows,
            "kept_rows": len(merged_rows),
            "dropped_rows": len(dropped),
        }
    )


@app.command()
def check(
    in_path: Path | None = typer.Option(None, "--in", help="Input records json/jsonl path"),
    out: Path | None = typer.Option(None, "--out", help="Output anomalies jsonl path"),
    config: str = typer.Option("configs/app.yaml", "--config", help="App config yaml"),
) -> None:
    if in_path is None:
        payload = {
            "python": {"ok": True},
            "docker": {"available": False},
            "note": "Run scripts/env_check.py for full environment details",
        }
        _echo_json(payload)
        return

    if not in_path.exists():
        _error_exit(ErrorCode.E1001, "Input records file not found", details={"path": str(in_path)})

    settings = load_settings(config)
    records = _load_invoice_records(in_path)
    records = attach_anomalies(records, config=settings.anomalies, templates=_load_template_overrides(settings))
    anomaly_rows = _build_anomaly_rows(records)
    output_path = out or Path("anomalies.jsonl")
    _append_jsonl(output_path, anomaly_rows)
    _echo_json(
        {
            "records": len(records),
            "anomaly_records": sum(1 for record in records if record.anomalies),
            "anomaly_count": len(anomaly_rows),
            "out": str(output_path),
        }
    )


@template_app.command("list")
def template_list() -> None:
    settings = load_settings("configs/app.yaml")
    specs = load_templates(settings.template_dir)
    _echo_json(
        {
            "templates": [
                {"template_id": spec.template_id, "doc_type": spec.doc_type, "locale": spec.locale}
                for spec in specs
            ]
        }
    )


@template_app.command("show")
def template_show(template_id: str) -> None:
    settings = load_settings("configs/app.yaml")
    registry = TemplateRegistry(load_templates(settings.template_dir))
    spec = registry.get(template_id)
    if spec is None:
        _error_exit(ErrorCode.E1001, "Template not found", details={"template_id": template_id})
    _echo_json(spec.model_dump(mode="json"))


@template_app.command("validate")
def template_validate(template_path: Path) -> None:
    spec = load_template(template_path)
    _echo_json({"template_id": spec.template_id, "valid": True})


@template_app.command("test")
def template_test(
    template_id: str,
    input_path: Path,
    out_dir: Path = typer.Option(Path("."), "--out"),
) -> None:
    settings = load_settings("configs/app.yaml")
    report = _build_template_test_report(template_id, input_path, out_dir, settings=settings)
    _echo_json(report)


@template_app.command("init")
def template_init(
    from_path: Path = typer.Option(..., "--from", exists=True, file_okay=True, dir_okay=False),
    out: Path = typer.Option(..., "--out"),
) -> None:
    _ = from_path
    template_payload = {
        "template_id": "generated",
        "version": "1.0.0",
        "locale": "zh-CN",
        "doc_type": "receipt",
        "aliases": {
            "issue_date": ["开票日期", "日期", "Date"],
            "total_amount_gross": ["价税合计", "合计", "Total Amount"],
        },
        "regex": {
            "issue_date": r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})",
            "total_amount_gross": r"([¥￥]?\s*\d+[.,]?\d{0,2})",
        },
        "anchors": {
            "issue_date": {"keywords": ["日期", "Date"], "roi": [0.0, 0.0, 1.0, 1.0], "direction": "right_or_below"},
            "total_amount_gross": {
                "keywords": ["合计", "Total"],
                "roi": [0.0, 0.0, 1.0, 1.0],
                "direction": "right_or_below",
            },
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(template_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _echo_json({"template_id": "generated", "out": str(out)})


@template_app.command("annotate")
def template_annotate(
    from_path: Path = typer.Option(..., "--from", exists=True, file_okay=True, dir_okay=False),
    out: Path = typer.Option(..., "--out"),
    template: str | None = typer.Option(None, "--template"),
    engine: str | None = typer.Option(None, "--engine"),
    pdf_mode: str | None = typer.Option(None, "--pdf-mode"),
) -> None:
    settings = load_settings("configs/app.yaml")
    active_settings = settings.model_copy(
        update={
            "ocr_engine": engine or settings.ocr_engine,
            "pdf_mode": pdf_mode or settings.pdf_mode,
        }
    )
    trace_id = new_trace_id()
    blocks = _collect_blocks(from_path, active_settings, trace_id, engine_name=engine, pdf_mode=pdf_mode)
    record = parse_file(from_path, config=active_settings, source_file_name=from_path.name)

    selected_template = _resolve_template_reference(template, active_settings)
    if selected_template is None:
        registry = TemplateRegistry(load_templates(active_settings.template_dir))
        selected_template = registry.select(blocks, record.doc_type, active_settings.locale)
    if selected_template is None:
        selected_template = TemplateSpec(
            template_id="auto_template",
            locale=active_settings.locale,
            doc_type=record.doc_type or "receipt",
            aliases={
                "merchant_name": ["商户", "商家", "store", "merchant"],
                "issue_date": ["日期", "date"],
                "total_amount_gross": ["合计", "total"],
                "merchant_tax_id": ["税号", "tax id"],
                "invoice_number": ["发票号", "invoice no"],
            },
        )

    pages_map: dict[int, dict[str, Any]] = {}
    for idx, block in enumerate(blocks):
        bbox = block.bbox if len(block.bbox) == 4 else [0.0, 0.0, 1.0, 1.0]
        _, _, x2, y2 = bbox
        page_item = pages_map.setdefault(
            block.page,
            {"page": block.page, "width": 1.0, "height": 1.0, "block_indices": []},
        )
        page_item["width"] = max(float(page_item["width"]), float(x2))
        page_item["height"] = max(float(page_item["height"]), float(y2))
        page_item["block_indices"].append(idx)

    serialized_blocks: list[dict[str, Any]] = []
    for block in blocks:
        page_item = pages_map.get(block.page, {"width": 1.0, "height": 1.0})
        raw = block.model_dump(mode="json")
        raw["bbox_norm"] = _normalize_bbox(
            block.bbox if len(block.bbox) == 4 else [0.0, 0.0, 0.0, 0.0],
            float(page_item["width"]),
            float(page_item["height"]),
        )
        serialized_blocks.append(raw)

    out.mkdir(parents=True, exist_ok=True)
    (out / "blocks.json").write_text(json.dumps({"blocks": serialized_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    pages_payload = {"pages": [pages_map[k] for k in sorted(pages_map)], "normalization": {"type": "per_page_max_bbox"}}
    (out / "pages.json").write_text(json.dumps(pages_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "template.json").write_text(
        json.dumps(selected_template.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "record.json").write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "template_update.json").write_text(
        json.dumps({"anchors": selected_template.model_dump(mode="json").get("anchors", {})}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "refine_report.json").write_text(
        json.dumps({"template_id": selected_template.template_id, "pages": len(pages_map), "blocks": len(blocks)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "editor.html").write_text(_editor_html(), encoding="utf-8")
    _echo_json({"out": str(out), "trace_id": trace_id, "template_id": selected_template.template_id})


@template_refine_app.command("apply")
def template_refine_apply(
    base: Path = typer.Option(..., "--base"),
    update: Path = typer.Option(..., "--update"),
    out: Path = typer.Option(..., "--out"),
) -> None:
    base_spec = load_template(base)
    update_payload = json.loads(update.read_text(encoding="utf-8"))
    merged = base_spec.model_dump(mode="python")
    anchors = dict(merged.get("anchors", {}))
    for field, value in (update_payload.get("anchors") or {}).items():
        anchors[field] = value
    merged["anchors"] = anchors
    merged_spec = TemplateSpec(**merged)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(merged_spec.model_dump(mode="python"), allow_unicode=True, sort_keys=False), encoding="utf-8")
    _ = load_template(out)
    _echo_json({"base": str(base), "update": str(update), "out": str(out), "valid": True})


@template_refine_app.command("test")
def template_refine_test(
    template: str = typer.Option(..., "--template"),
    sample: Path = typer.Option(..., "--sample"),
    out: Path = typer.Option(Path("."), "--out"),
) -> None:
    settings = load_settings("configs/app.yaml")
    template_spec = _resolve_template_reference(template, settings)
    if template_spec is None:
        _error_exit(ErrorCode.E1001, "Template not found", details={"template": template})

    run_settings = settings
    template_id = template_spec.template_id
    path_candidate = Path(template)
    if path_candidate.exists():
        temp_dir = out / ".tmp_refine_template"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_yaml = temp_dir / f"{template_id}.yaml"
        temp_yaml.write_text(
            yaml.safe_dump(template_spec.model_dump(mode="python"), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        run_settings = settings.model_copy(update={"template_dir": str(temp_dir)})
    report = _build_template_test_report(template_id, sample, out, settings=run_settings)
    _echo_json(report)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
