# M1-3 Done

## Scope
- Implemented template-aware extraction chain with registry-based selection.
- Added safe validator engine with whitelisted DSL operators.
- Implemented batch API job flow with sync/background execution and result endpoints.

## Completed
- Added template system:
  - `templates/models.py` (`TemplateSpec`, anchor/scoring rules)
  - `templates/loader.py` (`load_template`, `load_templates`)
  - `templates/registry.py` (`TemplateRegistry.select/get`)
  - sample template `configs/templates/default_receipt.yaml`
- Added `extractors/template_extractor.py`:
  - alias + regex + anchor-neighbor extraction
  - weighted scoring
  - provenance extractor tag `template:<template_id>`
- Runner chain integration:
  - template first, common extractor fallback for missing fields
  - template auto-select by `doc_type+locale` or explicit `template_id`
  - record now carries `template_id` and `validation_issues`
- Added safe validators (`validators/engine.py`): `required/gt/lt/eq/regex`
- CLI template commands implemented: `template list/show/validate/test`
- Batch API job implemented:
  - `POST /v1/batch`
  - `GET /v1/jobs/{job_id}`
  - `GET /v1/jobs/{job_id}/results`
  - filesystem job store under `settings.job_dir`

## Tests
- Added/verified M1-3 tests:
  - `test_template_load_validate.py`
  - `test_template_anchor_neighbor.py`
  - `test_template_select.py`
  - `test_chain_fallback.py`
  - `test_validators.py`
  - `test_api_batch_job_sync.py`

## Notes
- Optional dependencies mechanism remains unchanged and no hard deps were introduced.
- `/v1/parse` response remains `{trace_id, record}`.

