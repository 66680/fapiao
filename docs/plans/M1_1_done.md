# M1-1 Done

## Scope
- Implemented a minimal real parse pipeline with staged runner flow.
- Replaced mock-only parse entrypoints in API/CLI with runner integration.
- Added extractor + normalization modules and integration tests.

## Completed
- Added `src/invstruct/pipeline/runner.py` with stages:
  - ingest -> ocr -> classify -> extract -> normalize -> validate -> build record
- Added OCR abstractions:
  - `OcrTextBlock` and `OcrEngine` in `src/invstruct/ocr/base.py`
  - deterministic `MockOcrEngine` in `src/invstruct/ocr/mock.py`
- Added field extraction rules in `src/invstruct/extractors/common.py`.
- Added normalization helpers in `src/invstruct/normalize/common.py`.
- API `/v1/parse` now calls `runner.parse_path`.
- CLI `parse` now prints parsed record JSON.
- Added tests:
  - `tests/test_api_parse.py`
  - `tests/test_extract_common.py`

## Notes
- No PaddleOCR dependency added in M1-1.
- Soft validation updates `confidence.overall` without raising anomalies.

