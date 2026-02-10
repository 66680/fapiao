# M2-1 Done

## Scope
- Implemented exporter layer for xlsx summary report and csv details table.
- Added anomaly detection v0 for duplicate, amount mismatch, and low confidence/missing core fields.
- Extended CLI `batch/export/check` workflows for export integration and anomaly reporting.

## Completed
- Added `src/invstruct/exporters/report_xlsx.py`:
  - `write_report_xlsx(records, path)`
  - stable column order
  - bold header, freeze top row, autofilter
- Added `src/invstruct/exporters/details_csv.py`:
  - `write_details_csv(records, path)`
  - one row per field with provenance/confidence context
- Added anomalies package:
  - `src/invstruct/anomalies/models.py` (`Anomaly`)
  - `src/invstruct/anomalies/engine.py` (`attach_anomalies`)
- Extended schema:
  - `InvoiceRecord.anomalies` optional list field (default empty)
- Enhanced CLI:
  - `batch --export xlsx,csv [--xlsx ...] [--csv ...]` and report export metadata
  - `export --in <records.jsonl> --xlsx ... --csv ...` with robust record loading
  - `check --in <records.jsonl> --out <anomalies.jsonl>` anomaly output mode
- Added/updated tests:
  - `test_export_xlsx_has_columns.py`
  - `test_export_details_csv_rows.py`
  - `test_anomaly_duplicate_by_sha256.py`
  - `test_anomaly_amount_mismatch.py`
  - `test_anomaly_low_conf_missing_core.py`
  - `test_report_has_anomaly_columns.py`

## Verification
- `pip install -e .` passes.
- `pytest -q` passes (all green).
- CLI acceptance commands for `batch/export/check` execute with expected outputs.
