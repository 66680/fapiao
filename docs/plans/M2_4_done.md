# M2-4 Done

## Scope
- Implement export-template mapping wizard bundle (`wizard.html` + JSON artifacts).
- Add CLI refine apply/test for export templates.
- Add UI E2E regression via static artifact marker assertions.

## Completed
- Added wizard bundle generator:
  - `invstruct export templates wizard --in --base --out [--rows]`
  - outputs:
    - `export_template.json`
    - `sample_records.json`
    - `field_catalog.json`
    - `wizard.html`
    - `wizard_report.json`
- Added pure-static `wizard.html` (single-file, offline) with:
  - column add/remove/reorder
  - source/transform/default/required editing
  - transform whitelist enforcement (`as_is/date_iso/amount_2dp/anomaly_codes_join`)
  - preview table rendering from sample rows
  - export:
    - `export_template_update.json` (full template spec)
    - `wizard_refine_report.json`
- Added export-template refine commands:
  - `invstruct export templates refine apply --base --update --out`
  - `invstruct export templates refine test --template --in --out --report`
- Added tests:
  - `test_export_wizard_emits_required_files.py`
  - `test_wizard_html_contains_mapping_markers.py`

## Notes
- No strong dependencies added.
- No `eval` usage; transforms remain strict whitelist.
- Existing `M2-3` CLI/API behavior remains compatible.
