# M1-5.2 Done

## Scope
- Added keyboard ROI move/resize operations in static `editor.html`.
- Added undo/redo history for anchor edit actions.
- Added hotkeys overlay toggle and guidance.

## Completed
- Implemented keyboard nudge:
  - `Arrow` move ROI
  - step sizes: normal `0.005`, `Shift=0.02`, `Alt=0.001`
- Implemented keyboard resize:
  - `Ctrl + Arrow` adjust `x2/y2`
  - `Ctrl + Shift + Arrow` adjust `x1/y1`
- Added clamp and minimum ROI constraints (`minSpan` + `minArea`).
- Added history model (`historyStack/historyIndex`) and actions:
  - `Ctrl+Z` undo
  - `Ctrl+Shift+Z` redo
  - `Ctrl+Y` redo
- Added hotkeys overlay toggle with `?` or `H`.
- Added regression test `tests/test_editor_html_contains_undo_redo_and_nudge_markers.py`.

## Notes
- Keyboard shortcuts are ignored when `input/textarea` has focus.
- Existing interactions remain: click keyword selection, `Shift+Drag` live ROI, manual ROI input edits, JSON export.
