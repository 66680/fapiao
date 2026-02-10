# M2-3 Done

## Scope
- Added export-profile template system for accounting CSV mapping.
- Added mapped CSV exporter with safe transform whitelist.
- Extended CLI and API with export template management and job export endpoint.

## Completed
- Settings:
  - Added `export_template_dir` to `AppSettings` with YAML/env support.
- Export template system:
  - `src/invstruct/export_templates/models.py`
  - `src/invstruct/export_templates/loader.py`
  - sample templates:
    - `configs/export_templates/generic_expense_v1.yaml`
    - `configs/export_templates/generic_expense_minimal_v1.yaml`
- Exporter:
  - Added `src/invstruct/exporters/mapped_csv.py`
  - supported transforms (whitelist only):
    - `as_is`
    - `date_iso`
    - `amount_2dp`
    - `anomaly_codes_join`
- CLI:
  - Added `invstruct export accounting --in --template --out`
  - Added `invstruct export templates list/show/validate`
  - Preserved existing `invstruct export --in --xlsx --csv` behavior
- API:
  - Added `GET /v1/jobs/{job_id}/export`
  - supports `kind=report_xlsx|details_csv|accounting_csv`
  - `accounting_csv` requires `template_id`

## Tests
- Added:
  - `test_export_template_load_validate.py`
  - `test_mapped_csv_export_columns_order.py`
  - `test_cli_export_templates_list.py`
  - `test_api_job_export_accounting_csv.py`
- Existing tests remain green.
