# 07 Baseline Analysis and Improvement Plan

## Done (M0)
- Initialized `invstruct` repository scaffold with installable Python package.
- Added stable interfaces for CLI/API/config/errors/schema/trace/hash.
- Added mock OCR adapter and mock parse pipeline to keep M0 lightweight.
- Added six baseline tests for deterministic utilities and entrypoints.
- Added Docker CPU skeleton and compose setup for API boot/healthz.

## Next
- M1: implement real parser stages (ingest/preprocess/extract/normalize/validate).
- M1: add template loader and template validation command.
- M1: add export writer implementations for xlsx/csv.
- M1: add integration tests for `/v1/parse` and CLI `parse` with fixtures.

## Done (M1-1)
- Added staged parse runner (`parse_path`) and connected API/CLI to it.
- Added OCR abstraction with deterministic `MockOcrEngine` output blocks.
- Added rule-based common extractor for key fields and conflict resolution by score.
- Added date/amount normalization and lightweight soft-validation confidence adjustment.
- Added integration/unit tests for parse API and common extractor.

## Next (M1-2)
- Add real OCR adapter implementation (PaddleOCR optional plugin style, non-hard dependency).
- Extend parser to PDF multi-page ingestion and per-page provenance aggregation.
- Add template-aware extraction fallback chain (template -> common rules).
- Add CLI/API options to select OCR engine and template profile.

## Done (M1-2)
- Added optional PaddleOCR engine module with lazy dependency loading and explicit missing-dep errors.
- Added optional PDF renderer skeleton with lazy loading for `pypdfium2`/`Pillow`.
- Extended runner with configurable engine selection and PDF merge/per-page flows.
- Implemented CLI batch command outputs: `records.jsonl`, `failures.jsonl`, `run_report.json`.
- Added tests for missing optional dependencies to guarantee no hard dependency regressions.

## Next (M1-3)
- Add real PDF rendering integration tests under environments with `invstruct[pdf]` installed.
- Add paddle engine smoke tests under environments with `invstruct[paddle]` installed.
- Add batch-level API endpoint and asynchronous job tracking for large folders.
- Introduce template-aware field extraction chain with confidence blending.

## Done (M1-3)
- Added template-aware extraction chain with template registry, loader, and sample template config.
- Implemented template extractor with alias/regex/anchor-neighbor logic and weighted scoring.
- Integrated extraction fallback chain: template first, common extractor fills missing fields.
- Added safe validator DSL engine (`required/gt/lt/eq/regex`) without eval.
- Implemented CLI template commands (`list/show/validate/test`).
- Implemented batch API job endpoints with filesystem-backed job store and sync/background execution.
- Added M1-3 test suite for templates, chain fallback, validators, and batch sync API.

## Next (M1-4)
- Add template authoring helpers (interactive anchor capture and auto-suggest).
- Expand validator DSL with typed coercion and richer severity policies.
- Add batch job pagination and retention/cleanup policy.
- Add template evaluation benchmark suite over labeled fixture packs.

## Done (M1-4)
- Implemented template annotation assistant commands:
  - `template init` for semi-auto anchor generation and template YAML bootstrap
  - `template annotate` for OCR block pack export (`blocks.json`/`record.json`/`viewer.html`)
  - `template test` report enhancement with coverage and missing-field candidate details
- Implemented job lifecycle retention features:
  - enriched job state (`created_at`, `updated_at`, `bytes`, `n_files`, `status`)
  - cleanup engine with `retention_days`, `keep_last`, `dry_run`, and running-job protection
  - CLI job ops (`jobs list`, `jobs clean`)
  - API startup best-effort cleanup hook (configurable)
- Added M1-4 tests for template init validity and cleanup pruning behavior.

## Next (M1-5)
- Add human-in-the-loop template refinement UI for anchor/keyword adjustments.
- Add richer report visualizations for template_test and batch outputs.
- Add lifecycle policy options by status/type and archive-to-cold-storage support.
- Add concurrency-safe file locking for multi-process job writers.

## Done (M1-5)
- Added `template annotate` JSON pack outputs for refinement: `template.json`, `pages.json`, `blocks.json` (with `bbox_norm`), `record.json`.
- Added pure-static local `editor.html` for anchor keyword selection, ROI editing, direction update, and JSON export.
- Added CLI refine commands:
  - `template refine apply` for update JSON merge into YAML + validation
  - `template refine test` for sample evaluation and report output
- Added regression tests:
  - `test_annotate_emits_template_json.py`
  - `test_refine_apply_merges_anchors.py`
- Kept `/v1/parse` response shape unchanged.

## Next (M1-6)
- Add image overlay snapshots in refinement outputs for quick visual QA.
- Add field-level diff view between base template and refine updates.
- Add batch template A/B comparison reports over fixture sets.
- Add optional lockfile for concurrent CLI refine apply operations.

## Done (M0 closure hardening)
- Unified error payload entrypoint to `error_payload(...)` with compatibility alias `as_error_payload`.
- Verified local baseline remains green: editable install, pytest full pass, CLI help, uvicorn `/healthz`.
- Added `scripts/env_check.py` for structured environment readiness checks (Python/pip/docker visibility).
- Hardened Docker static config (`docker/Dockerfile.cpu`, `docker-compose.yml`) for src-layout packaging and uvicorn entrypoint.
- Recorded Docker validation blocker and workaround in `docs/plans/M0_done.md`.

## Next (Docker-capable machine verification)
- Run `docker build -f docker/Dockerfile.cpu . -t invstruct:cpu` and record full logs.
- Run `docker run --rm -p 8000:8000 invstruct:cpu`, then verify `/healthz` returns `200` and `{"status":"ok"}`.
- Run `docker compose up --build`, then verify `/healthz` similarly and archive command outputs.

## Done (M1 MVP rules + batch/export)
- Added rule-first extractor module for merchant/date/amount/invoice/tax-id with provenance and confidence.
- Switched pipeline chain to use rules extractor as the shared fallback for CLI/API parse.
- Added `parse_file(...)` shared entrypoint to generate trace-aware records.
- Upgraded CLI `batch` to skip PDFs with `E3001` without aborting whole run.
- Implemented CLI `export` to CSV/XLSX with stable summary columns.
- Wired API `/v1/parse` to shared `parse_file` pipeline.
- Added focused tests for rules, pipeline trace/sha, CLI parse/batch, export, and API parse.

## Next (M1 follow-up)
- Add richer template precedence strategy and conflict diagnostics.
- Expand PDF support from stub behavior to controlled multi-page parsing.
- Add async job persistence and pagination for batch API endpoints.

## Done (M1.1 PDF skipped-record alignment)
- Upgraded CLI `batch` so PDF inputs emit placeholder records in `records.jsonl` with `status=skipped`.
- Added optional error fields on records for downstream exports: `error_code`, `error_message`.
- Preserved single-file parse behavior for PDF (`E3001` error payload) to avoid API/CLI contract breaks.
- Extended export outputs with `status/error_code/error_message` columns for CSV/XLSX alignment.
- Added tests for skipped record emission, export columns, and parse-PDF error behavior.

## Next (M1.2 PDF parser path)
- Replace PDF stub behavior with real multipage parsing and per-page provenance aggregation.
- Define skip vs fail policy for partial PDF ingestion failures and capture deterministic retry metadata.

## Done (M1.2 PDF text parsing opt-in)
- Implemented opt-in PDF parsing via `pdfplumber` with multi-page text block extraction.
- Preserved compatibility defaults: CLI/API single-file parse still returns `E3001` unless `allow_pdf` is explicitly enabled.
- Upgraded batch PDF flow: default skip remains, opt-in parsing produces `status=success` records when extraction succeeds.
- Added partial-page warning capture (`warnings`) plus deterministic retry metadata (`retry_key`) and parser metadata (`parser_version`).
- Added tests for opt-in CLI PDF parse success, batch upgrade behavior with `--allow-pdf`, and deterministic retry key generation.

## Next (M1.3 PDF quality hardening)
- Improve PDF table/receipt layout grouping for better field extraction accuracy under noisy line segmentation.
- Add API-level PDF parse tests for `allow_pdf=true` and default error compatibility.
- Add richer page-level diagnostics in exported run reports for skipped/failed PDF records.

## Done (M1.3 PDF quality hardening)
- Added configurable PDF line grouping controls (`pdf_enable_line_merge`, `pdf_line_merge_y_tol`) to support rollback/tuning.
- Hardened `pdfplumber` word-to-line merge for mixed layout receipts with merged bbox and stable token join rules.
- Added API tests for PDF default compatibility (`E3001`) and opt-in success (`allow_pdf=true`).
- Enhanced batch diagnostics by writing `run_report.json` with summary counts and per-file trace/retry/error fields.
- Enhanced export diagnostics with warnings metadata columns (`warnings_count`, `warnings_json`) and parser/retry fields.

## Next (M1.4 extraction quality tuning)
- Calibrate locale-specific spacing and numeric join heuristics for bilingual invoices.
- Add benchmark fixtures with multi-column receipts to monitor regression on amount/date extraction precision.
- Add optional debug artifacts (page line clusters) for failed PDF parsing investigations.

## Done (M1.4 extraction quality tuning)
- Introduced configurable rules tuning parameters (`rules_amount_keyword_window`, keyword preference toggles, normalization toggle, debug top-k).
- Reworked rules candidate scoring for amount/date/invoice/tax extraction with explicit confidence reasons and keyword-distance weighting.
- Added six benchmark block fixtures under `tests/fixtures/blocks_cases` and parameterized regression test coverage.
- Added optional CLI debug artifacts for `parse`/`batch` to persist normalized lines, top candidates, and final selection reasoning.
- Added tests to verify debug artifacts are only written when enabled and benchmark expectations stay stable.

## Done (M1.5 warnings cleanup + OCR fixtures engine)
- Removed FastAPI startup deprecation warnings by migrating from `@app.on_event("startup")` to lifespan startup hook.
- Added OCR engine skeleton method `extract_blocks(...)` with compatibility bridge `recognize(...)`.
- Added `FixturesOcrEngine` to replay OCR blocks from `<name>.blocks.json` and `.invstruct.blocks.jsonl` without real OCR dependencies.
- Added CLI `parse`/`batch` options `--ocr-engine` and `--fixtures-dir`, defaulting to existing behavior when not set.
- Added regression tests for warning cleanliness, fixtures-engine end-to-end parse, batch fixtures processing, and CLI help coverage.

## Next (M1.5 evaluation and drift control)
- Build automated quality scorecards from benchmark fixtures to track confidence drift over time.
- Add fixture packs with noisy OCR/token fragmentation patterns from real bilingual invoices.
- Add lightweight alerting when rule confidence drops below threshold on benchmark suite.

## Done (M1.6 export stability + merge dedup)
- Added CLI `merge` command for multi-file records merge with deterministic dedup key priority (`sha256` then `retry_key` then `doc_id`).
- Added merge conflict strategy (`success > skipped > failed`, then higher `confidence.overall`, then stable doc_id tiebreak).
- Added `merge_report.json` with kept/dropped counts and reason statistics for auditability.
- Stabilized export schema for mixed record versions by filling missing fields and preserving stable CSV/XLSX diagnostic columns.
- Added regression tests for merge dedup behavior, export column/type stability, API batch export response compatibility, and CLI export entrypoint compatibility.

## Next (M1.7 data quality controls)
- Add configurable dedup strategy profiles (strict sha256 / business-key hybrid / temporal window).
- Add merge conflict traceability with full kept-vs-dropped snapshot hashes.
- Add export-level schema version stamping for downstream ETL compatibility checks.

## Done (M1.7 data quality controls)
- Added merge dedup profile selector (`--dedup-profile`) with supported modes `strict_sha256`, `business_key_hybrid`, and `temporal_window`.
- Kept default merge behavior compatible while extending report telemetry with `dedup_profile` and `key_type_stats`.
- Added canonical JSON snapshot hashing for merge conflicts and persisted kept/dropped hashes in `merge_report.json`.
- Added export schema version stamping:
  - CSV header comments with schema version and generation metadata (default on, opt-out via `--no-header-comments`)
  - XLSX `_meta` sheet containing schema version and metadata fields.
- Added regression tests for profile behavior, conflict traceability hash stability, and export schema stamping compatibility.

## Next (M1.8 downstream contract governance)
- Add configurable schema version policy checks (strict/flexible) for ETL consumers.
- Add merge report compaction options for large conflict sets.
- Add profile-level metrics export for dedup drift monitoring.

## Done (M1-5.1)
- Upgraded static `editor.html` ROI interaction to live drag visualization with:
  - `dragRect` rubber-band rectangle
  - `coordHUD` live normalized coordinates + area display
  - real-time ROI input sync during drag
  - `Shift + Drag` gating to avoid click-mode conflicts
  - `Escape` cancel support
  - ROI clamp to `[0,1]` and minimum-area commit guard
- Kept template refinement JSON I/O contracts unchanged.
- Added regression test `test_editor_html_contains_live_roi_markers.py`.

## Next (M1-5.2)
- Add keyboard nudging (arrow keys) for fine ROI adjustment.
- Add per-field undo/redo history in the static editor session.
- Add hover-to-preview matched anchor candidates before commit.
- Add optional snap-to-block bounds while maintaining manual override.

## Done (M1-5.2)
- Added keyboard ROI editing in static `editor.html`:
  - `Arrow` move ROI
  - `Ctrl + Arrow` resize `x2/y2`
  - `Ctrl + Shift + Arrow` resize `x1/y1`
  - step control with `Alt=0.001`, normal `0.005`, `Shift=0.02`
- Added ROI safety constraints: clamp to `[0,1]`, min span, and min area guard.
- Added history-based editing state (`historyStack/historyIndex`) with:
  - undo: `Ctrl+Z`
  - redo: `Ctrl+Shift+Z` and `Ctrl+Y`
- Added hotkeys overlay toggle (`?` / `H`) and retained existing click/drag/input/export flows.
- Added regression test `test_editor_html_contains_undo_redo_and_nudge_markers.py`.

## Next (M1-5.3)
- Add per-field history scope switch (global vs current-field only).
- Add anchor edge handles for mouse-only resize without keyboard.
- Add optional snap-grid and block-edge snapping controls.
- Add audit trail panel of recent edit actions in editor session.

## Done (M2-1)
- Added export modules:
  - `write_report_xlsx` (stable summary columns + header style/freeze/autofilter)
  - `write_details_csv` (field-level details with provenance/confidence)
- Added anomalies v0:
  - duplicate by `sha256` and business-key
  - amount mismatch (`subtotal + tax != total`)
  - low confidence and missing core-field detection
- Extended `InvoiceRecord` with optional `anomalies` list.
- Enhanced CLI workflows:
  - `batch` supports `--export xlsx,csv` plus custom output paths and writes export status into `run_report.json`
  - `export --in ... --xlsx ... --csv ...` robustly loads records and emits outputs
  - `check --in ... --out ...` writes anomaly JSONL summary
- Added M2-1 test coverage for exporter columns/rows and anomaly rules.

## Next (M2-2)
- Add anomaly thresholds and rule toggles via config/template.
- Add dedupe window strategies (same day / same vendor / same amount bands).
- Add batch export bundling (single command output package with report/anomaly/artifacts).
- Add API endpoints for anomaly scan and export generation.

## Done (M2-2)
- Added anomaly config to `AppSettings` with nested rule models:
  - duplicate (`enabled/use_sha256/use_business_key/business_key_fields`)
  - amount mismatch (`enabled/tolerance`)
  - low confidence (`enabled/threshold/require_core_fields/missing_severity`)
- Added template-level anomaly overrides in `TemplateSpec` (`anomalies` optional, partial override).
- Implemented effective anomaly config merge:
  - global base from `configs/app.yaml`
  - template-level overrides by `record.template_id`
- Updated anomaly engine and CLI anomaly flows:
  - `batch` applies config-aware anomalies before export output generation
  - `export` applies config-aware anomalies when writing outputs
  - `check` supports `--config` and applies template override merge
- Added env consistency support:
  - `INVSTRUCT_LOW_CONF` syncs low-conf anomaly threshold
  - `INVSTRUCT_AMOUNT_TOLERANCE` overrides amount mismatch tolerance
- Added M2-2 regression tests for config/template override behavior.

## Next (M2-3)
- Add per-rule anomaly explanations with remediation hints in export/report.
- Add configurable duplicate windowing (date/vendor/amount fuzzy matching).
- Add API route for anomaly-only scan with configurable profiles.
- Add template authoring guidance for anomaly override presets.

## Done (M2-3)
- Added export profile template system for accounting CSV mapping with loader + schema validation.
- Added mapped CSV exporter with whitelist-only transforms:
  - `as_is`
  - `date_iso`
  - `amount_2dp`
  - `anomaly_codes_join`
- Added default accounting export templates:
  - `generic_expense_v1`
  - `generic_expense_minimal_v1`
- Added CLI export profile commands:
  - `invstruct export templates list/show/validate`
  - `invstruct export accounting --in --template --out`
- Added API export endpoint:
  - `GET /v1/jobs/{job_id}/export?kind=...`
  - supports `report_xlsx`, `details_csv`, `accounting_csv`
- Added regression tests for template load, mapped CSV column order, CLI template listing, and API job accounting export.

## Next (M2-4)
- Add profile-level default values and per-column fallback chains.
- Add transform options (round mode/date parse locale) with strict schema validation.
- Add async export artifact persistence with signed download URLs.
- Add API-side profile discovery endpoint for UI integration.

## Done (M2-4)
- Added export-template mapping wizard CLI:
  - `invstruct export templates wizard --in --base --out [--rows]`
  - emits `export_template.json`, `sample_records.json`, `field_catalog.json`, `wizard.html`, `wizard_report.json`
- Added pure-static `wizard.html` (single-file offline, no CDN) with JSON-driven mapping editing:
  - add/remove/reorder columns
  - edit `source/transform/default/required`
  - preview rendered rows from `sample_records.json`
  - download `export_template_update.json` and `wizard_refine_report.json`
- Added export template refine lifecycle:
  - `invstruct export templates refine apply --base --update --out`
  - `invstruct export templates refine test --template --in --out --report`
- Added regression tests for static wizard artifact generation and UI marker presence.

## Next (M2-5)
- Add per-column source fallback chains (`source_candidates`) for sparse datasets.
- Add template diff report between base and refined export specs.
- Add API endpoint for export template discovery and validation preview.
- Add optional server-side preview endpoint for accounting CSV dry-run.

## Done (M2-5)
- Added `source_candidates` fallback chain to export template columns while keeping `source` backward compatible.
- Implemented mapped CSV first-non-empty candidate resolution with safe empty checks (numeric `0` kept as valid).
- Extended export refine test report with `fallback_usage_by_column` stats.
- Upgraded static export wizard UI to edit candidate list per column (add/remove/reorder), with preview based on fallback resolution.
- Added export template diff command:
  - `invstruct export templates diff --a --b --out --format json,md`
  - outputs `diff_report.json` and `diff_report.md`
  - reports added/removed/modified/moved columns
- Added regression tests for loader fallback model, exporter fallback behavior, wizard candidate markers, and diff report generation.

## Next (M2-6)
- Add weighted candidate priority tuning and optional field-level fallback strategy profiles.
- Add template diff view for transform/default/required changes with richer markdown tables.
- Add API endpoints for export template wizard bundle generation and diff preview.
- Add optional export dry-run API response containing preview rows and fallback traces.

## Done (M2-6)
- Added export preview core `preview_mapped(...)` with reusable fallback/source usage stats.
- Added export API endpoints:
  - `GET /v1/export/templates`
  - `POST /v1/export/preview`
  - `GET /v1/jobs/{job_id}/export/preview`
- Implemented top-N preview safety (preview endpoints cap rows and avoid large in-memory previews).
- Enhanced diff markdown output to table-based sections while keeping diff JSON shape unchanged.
- Added `candidate_strategy` to export columns with backward-compatible default:
  - `first_non_empty` (default)
  - `prefer_primary_source`
  - `highest_confidence` (placeholder strategy path)
- Added M2-6 regression tests for preview APIs, markdown table output, and candidate strategy behavior.

## Next (M2-7)
- Add per-column strategy config in wizard UI with explainable preview traces.
- Add API-side validation endpoint for export templates with strict warnings/errors split.
- Add preview sampling modes (`head`, `stratified`) for large job datasets.
- Add diff markdown rendering of per-field before/after values as expanded tables.

## Done (M2-7)
- Improved OpenAPI usability:
  - added route summaries/descriptions/tags
  - added API response models for health/parse/batch/export preview flows
  - wired error envelope model usage on key API routes
- Standardized API error payload generation for non-exception route branches.
- Normalized batch export download headers (`Content-Type`, `Content-Disposition`) via shared helper.
- Upgraded Docker demo packaging:
  - compose env/volume defaults for offline mock-engine operation
  - Dockerfile defaults for templates/export-templates/job dir
  - added `scripts/demo.sh` and `scripts/demo.ps1` runnable demos
- Reworked README top section for release-ready onboarding with copy-paste quickstarts and preview payload examples.
- Added regression test for export job header/content-disposition formatting and envelope error branch.

## Next (M3-0 hardening)
- Add OpenAPI examples for request payloads and error envelopes per endpoint.
- Add demo script assertions and optional smoke-test mode for CI.
- Add structured API auth placeholder design (token middleware hook without enforcement).
- Add release checklist automation (version bump, changelog, docs snapshot).

## Done (M3-0)
- Added release automation and check artifacts:
  - `docs/release/RELEASE_CHECKLIST.md`
  - `scripts/release_check.py`
  - `scripts/release.sh`
  - `scripts/release.ps1`
- Added offline OpenAPI export tooling:
  - `scripts/dump_openapi.py`
  - outputs `docs/api/openapi.json` via `app.openapi()`
- Added API example documentation:
  - `docs/api/examples.md` (curl / PowerShell / python requests for parse, batch, preview, export)
- Updated packaging dev extras to include `build`, and release scripts now execute `python -m build`.
- Added optional minimal GitHub Actions CI:
  - multi-OS / multi-python pytest matrix
  - OpenAPI artifact upload
  - dist artifact build/upload job
- Maintained API compatibility, including `/v1/parse` response shape.

## Next (M3-1 release polish)
- Add changelog generation and version bump helper script.
- Add preflight check for template/schema drift against fixture pack.
- Add signed release asset manifest for `dist` and `openapi.json`.
- Add optional smoke job that runs demo scripts against local uvicorn instance.

## Done (M3-1)
- Added release metadata foundations:
  - `CHANGELOG.md` with `Unreleased` and `0.1.0` sections
  - `docs/release/RELEASE_NOTES_TEMPLATE.md`
- Added version bump automation:
  - `scripts/bump_version.py` (`--patch` / `--to`)
  - synchronized updates for `pyproject.toml` and `src/invstruct/__init__.py`
- Hardened release preflight checks:
  - `scripts/release_check.py` now validates `project.version == __version__`
  - checks required M3-1 release assets/scripts existence
- Added release bundle automation:
  - `scripts/package_release.py` generates `release/invstruct_<ver>_release_bundle.zip`
  - emits matching checksum file `.sha256`
  - bundle includes `dist/*`, OpenAPI, API examples, and demo scripts
- Added release notes generation helper:
  - `scripts/generate_release_notes.py`
- Updated release pipelines:
  - `scripts/release.sh` and `scripts/release.ps1` now run package + notes + final strict check
  - CI `build-dist` job uploads release bundle artifacts
- Added regression coverage for version consistency checks:
  - `tests/test_release_check_version_consistency.py`

## Next (M3-2)
- Add changelog linting rules (heading/date/version format) into release checks.
- Add bundle manifest JSON with per-file hashes and sizes.
- Add optional smoke-test mode in CI using uvicorn + demo API calls.
- Add signed artifact workflow hooks for external release channels.

## Done (Sync codex -> git repo)
- Mirrored full project tree from `D:\huashu\codex` into git repo workspace `D:\project demo\invstruct` (excluding `.git/.venv/dist/release` and local caches).
- Removed stale legacy files that conflicted with the synchronized codebase (mirror mode) and aligned test/script surface to the latest release-ready tree.
- Verified full regression in real git repo:
  - `pytest -q` passed with `87` tests.
  - `scripts/release.ps1` rehearsal completed with `exit_code=0`.
  - `scripts/release_check.py --strict` passed after syncing `docs/release/*`.
- Verified release bundle content now includes only current version dist artifacts.

## Next (M3-2 execution)
- Push sync branch to remote and open PR for review.
- Tag `v0.1.0` after PR merge and CI green.
- Publish GitHub Release with bundle zip + sha256 + release notes.

## Done (M3-2 release operations)
- Switched `origin` from `https://github.com/66680/OCR.git` to `https://github.com/66680/fapiao.git`.
- Pushed `invstruct-main` to new remote repository for initialization (`git push -u origin invstruct-main`).
