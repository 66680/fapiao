# M2-6 Done

## Scope
- Add export preview API (direct upload + by `job_id`).
- Upgrade diff markdown output to table format (JSON unchanged).
- Add candidate source strategy enum with backward-compatible default.

## Completed
- Added preview core:
  - `preview_mapped(rows, template, limit)` in `src/invstruct/exporters/preview.py`
  - output: `columns`, `rows`, `stats`
  - stats include fallback and per-source usage counters
- Added API routes:
  - `GET /v1/export/templates`
  - `POST /v1/export/preview` (multipart `records` + `template_id` or `template_yaml`)
  - `GET /v1/jobs/{job_id}/export/preview`
- Preview endpoints cap row count (`limit`, max 200) and only return top-N preview rows.
- Enhanced markdown diff report to tables:
  - metadata table
  - summary table
  - added/removed/modified/moved tables
- Added candidate strategy on export columns:
  - `first_non_empty` (default, unchanged behavior)
  - `prefer_primary_source`
  - `highest_confidence` (reserved behavior, currently same candidate pass)

## Tests Added
- `test_api_export_preview_returns_rows_and_stats.py`
- `test_api_job_export_preview.py`
- `test_diff_markdown_contains_tables.py`
- `test_candidate_strategy_prefer_primary.py`

## Verification
- `pytest -q` => all tests pass.
