$ErrorActionPreference = "Stop"

$BaseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://127.0.0.1:8000" }
$WorkDir = if ($args.Count -gt 0) { $args[0] } else { ".\out\demo" }
New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null

$SamplePng = Join-Path $WorkDir "sample.png"
$RecordsJsonl = Join-Path $WorkDir "records.jsonl"

[System.IO.File]::WriteAllBytes($SamplePng, [System.Text.Encoding]::UTF8.GetBytes("fake-image-bytes"))
@'
{"doc_id":"demo-1","merchant_name":"Demo Store","issue_date":"2026-02-09","total_amount_gross":12.34,"currency":"CNY","source":{"file_name":"demo.png","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","trace_id":"trace-demo-1"}}
'@ | Set-Content -Path $RecordsJsonl -Encoding UTF8

Write-Host "[1/6] healthz"
(Invoke-WebRequest -Uri "$BaseUrl/healthz" -UseBasicParsing).Content | Write-Host

Write-Host "[2/6] parse"
$parseForm = @{
    file = Get-Item $SamplePng
}
(Invoke-WebRequest -Uri "$BaseUrl/v1/parse" -Method Post -Form $parseForm -UseBasicParsing).Content | Write-Host

Write-Host "[3/6] export preview from upload"
$previewForm = @{
    records = Get-Item $RecordsJsonl
    template_id = "generic_expense_v1"
}
(Invoke-WebRequest -Uri "$BaseUrl/v1/export/preview" -Method Post -Form $previewForm -UseBasicParsing).Content | Write-Host

Write-Host "[4/6] create sync batch job"
$batchForm = @{
    files = Get-Item $SamplePng
}
$batchResp = Invoke-WebRequest -Uri "$BaseUrl/v1/batch?sync=true" -Method Post -Form $batchForm -UseBasicParsing
$batchPayload = $batchResp.Content | ConvertFrom-Json
$jobId = $batchPayload.job_id
$batchResp.Content | Write-Host
Write-Host "job_id=$jobId"

Write-Host "[5/6] export preview by job"
(Invoke-WebRequest -Uri "$BaseUrl/v1/jobs/$jobId/export/preview?template_id=generic_expense_v1&limit=5" -UseBasicParsing).Content | Write-Host

Write-Host "[6/6] download accounting csv"
$outCsv = Join-Path $WorkDir "accounting.csv"
Invoke-WebRequest -Uri "$BaseUrl/v1/jobs/$jobId/export?kind=accounting_csv&template_id=generic_expense_v1" -OutFile $outCsv -UseBasicParsing
Write-Host "saved: $outCsv"
