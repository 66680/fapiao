# M1 Plan (Day3-7)

## Goal
- Implement a minimal rule/template-first parsing chain that is shared by CLI and API.
- Deliver usable `parse/batch/export/check/template` command behaviors.
- Keep M0 contracts stable: error payload, trace/sha256, lightweight OCR adapter.

## In Scope
- Rules extractor for merchant/date/amount/invoice_no/tax_id with provenance and confidence.
- Shared pipeline function to produce `InvoiceRecord` from file path.
- CLI batch/export/check/template MVP behavior.
- API `/v1/parse` wired to shared pipeline.
- Tests for rules, pipeline, CLI, export, API.

## Out of Scope
- Real OCR model integration as required dependency.
- Full PDF multi-page parsing runtime.
- Template learning/training pipeline.

## Risks
- Locale-specific date parsing ambiguity.
- Template/rules precedence conflicts.
- Optional dependency behavior consistency.

## Mitigation
- Keep deterministic fallback rules with explicit precedence.
- Preserve existing error codes and payload structure.
- Add focused tests for critical extraction and command paths.

## M1.1: PDF stub skipped-record alignment
- Batch mode now emits a placeholder `InvoiceRecord` for each PDF input with `status=skipped`.
- Skipped records preserve `trace_id` and `sha256` so downstream evidence chain remains intact.
- Error context is embedded into optional fields: `error_code=E3001`, `error_message=PDF not supported yet`.
- Single-file parse semantics are unchanged: parsing PDF from `parse` still returns standard error payload.
- Export output is aligned with batch totals by adding `status/error_code/error_message` columns.

## M1.2: Real PDF text parsing (opt-in)
- Added PDF text parsing path backed by `pdfplumber` to extract multi-page text blocks and page-level provenance.
- Added explicit enable switches: CLI `--allow-pdf` and API `allow_pdf=true`; default behavior remains backward-compatible (`E3001`).
- Batch now supports parse-or-skip behavior for PDFs: default skip, opt-in parse success, and deterministic error record fallback.
- Introduced deterministic retry metadata (`retry_key`) and parser metadata (`parser_version`) on `InvoiceRecord`.
- Added page-level warning capture for partial extraction failures while still returning `status=success` when usable text exists.

## M1.3: PDF quality hardening
- Upgraded PDF word-to-line grouping with configurable Y-cluster tolerance and line-merge switch.
- Improved line text join strategy for mixed CJK/Latin/amount tokens to reduce fragmented extraction misses.
- Kept provenance chain complete (`page`, merged `bbox`, plus downstream `line_id`/`line_text` from extractor stage).
- Added API regression tests for default PDF rejection (`E3001`) and opt-in parse success (`allow_pdf=true`).
- Enhanced batch/export diagnostics with `run_report.json` per-file summary and export columns `warnings_count` / `warnings_json`.

## M1.4: Extraction quality tuning
- Added rule-tuning config knobs for amount/date normalization and keyword preference with environment overrides.
- Reworked rules extraction scoring for bilingual amount/date/invoice/tax cases with explainable confidence reasons.
- Added benchmark fixture pack (`tests/fixtures/blocks_cases`) with six deterministic block scenarios for regression safety.
- Added optional debug artifacts (`--debug-artifacts`) to CLI parse/batch, writing normalized lines, candidates, and selected reasons.
- Added regression tests for benchmark fixtures and debug artifact generation while preserving default compatibility behavior.

## M1.5: Warnings cleanup + OCR engine skeleton
- Replaced FastAPI startup `on_event` hook with lifespan startup handler to remove deprecation warnings in test output.
- Added OCR engine skeleton unification via `extract_blocks(...)` while keeping `recognize(...)` backward compatibility.
- Added `FixturesOcrEngine` for deterministic end-to-end replay from `<name>.blocks.json` or `.invstruct.blocks.jsonl`.
- Added CLI overrides `--ocr-engine auto|mock|fixtures` and `--fixtures-dir` for parse/batch, default behavior unchanged.
- Added regression tests for warnings cleanliness, fixtures-engine parse/batch roundtrip, and CLI help option visibility.

## M1.6: Export stability + merge dedup + compatibility regressions
- Added `merge` CLI command to combine multiple records files with deterministic dedup key priority (`source.sha256` > `retry_key` > `doc_id`).
- Implemented conflict resolution priority for merge (`success > skipped > failed`, then higher confidence), and wrote `merge_report.json`.
- Hardened export summary/report columns with stable ordering and explicit diagnostics (`status/error_code/error_message/warnings_count/parser_version/retry_key`).
- Ensured export handles mixed legacy/new records with missing fields without crashing CSV/XLSX generation.
- Added compatibility regression tests for CLI export entrypoints and API batch export response branches.

## M1.7: Data quality controls
- Added configurable merge dedup profiles (`strict_sha256`, `business_key_hybrid`, `temporal_window`) with default behavior preserved.
- Enhanced merge audit trail with canonical snapshot hashes and per-conflict kept-vs-dropped traceability.
- Added merge report metadata (`dedup_profile`, `key_type_stats`, `snapshot_hash_algorithm`, `conflicts`) for deterministic review.
- Added export schema version stamping for downstream ETL checks:
  - CSV header comments (default on, disable with `--no-header-comments`)
  - XLSX `_meta` sheet with schema version and generation metadata.
- Added regression tests for dedup profiles, conflict traceability hashes, and schema version stamping.
