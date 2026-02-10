# M2-2 Done

## Scope
- Made anomaly thresholds/rules configurable from global app settings.
- Added template-level anomaly override support in `TemplateSpec`.
- Applied effective anomaly config merge in CLI anomaly paths (`batch/export/check`).

## Completed
- Extended `AppSettings` with nested anomaly config models:
  - `DuplicateConfig`
  - `AmountMismatchConfig`
  - `LowConfConfig`
- Added `anomalies` block loading from YAML (`configs/app.yaml`) with backward-compatible defaults.
- Added env compatibility and overrides:
  - `INVSTRUCT_LOW_CONF` syncs `anomalies.low_conf.threshold`
  - `INVSTRUCT_AMOUNT_TOLERANCE` overrides amount mismatch tolerance
- Extended `TemplateSpec` with optional `anomalies` overrides (partial and backward-compatible).
- Added effective config merge in anomaly engine:
  - base from `settings.anomalies`
  - per-template override by `record.template_id`
- Updated CLI to use effective anomaly config:
  - `batch` anomaly detection before exports
  - `export` anomaly-aware report generation
  - `check --config ...` anomaly scan using global + template overrides

## Tests
- Added:
  - `test_anomaly_config_override_low_conf_threshold.py`
  - `test_template_anomaly_override_disables_duplicate.py`
  - `test_amount_mismatch_tolerance_override.py`
- Updated template/config loading tests for new anomaly config compatibility.

## Verification
- `pip install -e .` passes.
- `pytest -q` passes.
- `batch/export/check` acceptance commands pass with config-aware anomaly behavior.
