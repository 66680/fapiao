# M1-5 Done

## Scope
- Added static `editor.html` refinement workflow driven by local JSON files.
- Extended `template annotate` to emit `template.json`, `pages.json`, normalized `blocks.json`, and refinement seeds.
- Added CLI commands for `template refine apply` and `template refine test`.
- Added tests for annotate artifact generation and refine anchor merge behavior.

## Completed
- Implemented `invstruct template annotate --from ... --out ... [--template] [--engine] [--pdf-mode]`.
- Implemented `invstruct template refine apply --base --update --out` with YAML merge + schema validation.
- Implemented `invstruct template refine test --template --sample --out` and report export.
- Added `tests/test_annotate_emits_template_json.py`.
- Added `tests/test_refine_apply_merges_anchors.py`.
- Updated README with Template Refinement Workflow section.

## Notes
- `editor.html` is pure static HTML/JS with no external network dependencies.
- Browser only reads JSON (`blocks.json`, `pages.json`, `template.json`) and exports JSON (`template_update.json`, `refine_report.json`).
- `/v1/parse` response structure is unchanged.
