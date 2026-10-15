param([ValidateRange(1024,65535)][int]$Port = 8501)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine unavailable. Start Docker Desktop Linux engine; see docs/DEPLOYMENT.md.' }
$previousHostPort = $env:BATTERYTWIN_HOST_PORT
$env:BATTERYTWIN_HOST_PORT = "$Port"
try {
    & docker compose -p batterytwin-streamlit config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration invalid.' }
    & docker compose -p batterytwin-streamlit up -d --build --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Build or container health failed. Inspect: docker compose -p batterytwin-streamlit logs' }
    $baseUrl = "http://127.0.0.1:$Port"
    $health = Invoke-WebRequest -Uri "$baseUrl/_stcore/health" -TimeoutSec 30
    if ($health.StatusCode -ne 200) { throw 'Streamlit health verification failed.' }
    & docker compose -p batterytwin-streamlit exec -T batterytwin python scripts/smoke_inference.py
    if ($LASTEXITCODE -ne 0) { throw 'Saved-model inference verification failed.' }
    Write-Host "Streamlit Docker deployment verified: $baseUrl"
    Write-Host 'Stop deployment: docker compose -p batterytwin-streamlit down'
} finally {
    if ($null -eq $previousHostPort) { Remove-Item Env:BATTERYTWIN_HOST_PORT -ErrorAction SilentlyContinue }
    else { $env:BATTERYTWIN_HOST_PORT = $previousHostPort }
}
