# M1-2 Done

## Scope
- Added optional PaddleOCR engine and optional PDF render skeleton with lazy imports.
- Added PDF merge/per-page branching in pipeline runner.
- Implemented CLI batch output artifacts (`records.jsonl`, `failures.jsonl`, `run_report.json`).

## Completed
- `config` extended with `ocr_engine`, `pdf_mode`, `max_pdf_pages` plus env overrides.
- Added `ocr/paddle.py` lazy loading `paddleocr` and raising `OcrError(E2001)` on missing deps.
- Added `pdf/render.py` lazy loading `pypdfium2`/`Pillow` and raising `InputError(E1001)` on missing deps.
- `pipeline/runner.py` supports:
  - engine selection by settings (`mock` / `paddle`)
  - PDF merge mode in `parse_path`
  - PDF per-page mode in `parse_path_multi`
- CLI parse supports `--engine` and `--pdf-mode`.
- CLI batch implemented with JSONL outputs and run report.
- API `/v1/parse` now reads engine/pdf mode from settings while preserving single-record response.
- Added optional extras in `pyproject.toml`: `pdf`, `paddle`.
- Added tests for missing optional dependencies:
  - `test_paddle_missing_dep.py`
  - `test_pdf_missing_dep.py`

## Notes
- Importing `invstruct` and running tests works without installing optional deps.
- API default remains single record response (`merge` mode).

