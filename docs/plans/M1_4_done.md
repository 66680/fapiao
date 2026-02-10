# M1-4 Done

## Scope
- Added template annotation assistant workflow (init/annotate/test-report).
- Added job retention and cleanup subsystem (CLI + API startup best-effort cleanup).

## Completed
- Template init (`invstruct template init`):
  - OCR-driven semi-auto anchor generation for `issue_date`, `total_amount_gross`, `merchant_tax_id`, `invoice_number`
  - ROI inference via bbox expansion + normalization
  - optional interactive keyword override
  - outputs template YAML + `template_init_report.json`
- Template annotate (`invstruct template annotate`):
  - outputs `blocks.json`, `record.json`, and optional `viewer.html`
- Template test report enhancement:
  - `template_test_report.json` with coverage + missing fields + top candidates
- Job retention/cleanup:
  - config: `job_retention_days`, `job_keep_last`, `job_cleanup_on_startup`
  - batch job state now tracks `created_at`, `updated_at`, `bytes`, `n_files`, `status`
  - cleanup function `cleanup_jobs(...)` with `dry_run` and running-job protection
  - CLI: `invstruct jobs list`, `invstruct jobs clean --dry-run`
  - API startup hook triggers best-effort cleanup when enabled

## Tests
- Added `tests/test_template_init_generates_valid_yaml.py`
- Added `tests/test_jobs_cleanup_prunes_old.py`
- Full suite remains green.

## Notes
- No new hard dependencies introduced.
- Template YAML emitted by `template init` validates against `TemplateSpec`.
- Cleanup never deletes jobs in `running` state.

