# M2-5 Done

## Scope
- Add `source_candidates` fallback chain for accounting export templates.
- Extend static wizard to edit candidate sources.
- Add export template diff reports (`json` + `md`).

## Completed
- `ExportColumnSpec` supports:
  - `source` (backward compatible)
  - `source_candidates` (optional fallback list)
  - validation rule: at least one of `source` / `source_candidates` is required
- Mapped CSV exporter fallback implemented:
  - resolves first non-empty candidate value
  - keeps `0` as valid value (not treated as empty)
  - preserves transform whitelist behavior
- Export refine test report now includes `fallback_usage_by_column`.
- Static `wizard.html` updated for candidate editing:
  - add/remove/reorder candidate sources per column
  - preview uses candidate resolution and exposes used source in cell tooltip
  - includes test markers `sourceCandidatesList` and `addCandidateBtn`
- Added `export templates diff` command:
  - `invstruct export templates diff --a --b --out --format json,md`
  - writes `diff_report.json` and/or `diff_report.md`
  - detects added/removed/modified/moved columns

## Tests Added
- `test_export_template_loader_accepts_source_candidates.py`
- `test_mapped_csv_uses_source_candidates_fallback.py`
- `test_wizard_html_contains_source_candidates_markers.py`
- `test_export_templates_diff_report_detects_changes.py`

## Notes
- No strong dependency added.
- No `eval` introduced.
- Existing M2-4/M2-3 CLI/API behavior remains compatible.
