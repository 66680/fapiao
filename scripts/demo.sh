#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
WORK_DIR="${1:-./out/demo}"
mkdir -p "$WORK_DIR"

SAMPLE_PNG="$WORK_DIR/sample.png"
RECORDS_JSONL="$WORK_DIR/records.jsonl"

printf 'fake-image-bytes' > "$SAMPLE_PNG"
cat > "$RECORDS_JSONL" <<'EOF'
{"doc_id":"demo-1","merchant_name":"Demo Store","issue_date":"2026-02-09","total_amount_gross":12.34,"currency":"CNY","source":{"file_name":"demo.png","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","trace_id":"trace-demo-1"}}
EOF

echo "[1/6] healthz"
curl -sS "$BASE_URL/healthz"
echo

echo "[2/6] parse"
curl -sS -F "file=@${SAMPLE_PNG};type=image/png" "$BASE_URL/v1/parse"
echo

echo "[3/6] export preview from upload"
curl -sS -F "records=@${RECORDS_JSONL};type=application/json" -F "template_id=generic_expense_v1" "$BASE_URL/v1/export/preview"
echo

echo "[4/6] create sync batch job"
BATCH_RESP="$(curl -sS -F "files=@${SAMPLE_PNG};type=image/png" "$BASE_URL/v1/batch?sync=true")"
echo "$BATCH_RESP"
JOB_ID="$(python -c "import json,sys; print(json.loads(sys.stdin.read())['job_id'])" <<< "$BATCH_RESP")"
echo "job_id=$JOB_ID"

echo "[5/6] export preview by job"
curl -sS "$BASE_URL/v1/jobs/${JOB_ID}/export/preview?template_id=generic_expense_v1&limit=5"
echo

echo "[6/6] download accounting csv"
curl -sS -o "$WORK_DIR/accounting.csv" "$BASE_URL/v1/jobs/${JOB_ID}/export?kind=accounting_csv&template_id=generic_expense_v1"
echo "saved: $WORK_DIR/accounting.csv"
