# M1-5.1 Done

## Scope
- Upgraded static `editor.html` ROI drawing from mouseup-only to live drag visualization.
- Kept JSON contracts unchanged (`template.json`, `blocks.json`, `pages.json`, `template_update.json`).
- Added regression test for required live-ROI editor markers.

## Completed
- Added `dragRect` rubber-band rectangle overlay.
- Added `coordHUD` live coordinate/area panel.
- Added `pointerdown/pointermove/pointerup` drag workflow with `Shift` gating.
- Added live ROI input sync while dragging.
- Added `Escape` cancel handling.
- Added clamp to `[0,1]` and minimum-area guard before committing ROI.
- Added test `tests/test_editor_html_contains_live_roi_markers.py`.

## Notes
- Normal click behavior for keyword selection remains intact.
- Drag ROI is active only under `Shift + Drag`, preventing click-mode conflicts.
