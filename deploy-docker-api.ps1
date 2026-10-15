param(
    [ValidateRange(1024,65535)]
    [int]$Port = 8001
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker is not installed. Install Docker Desktop and start its Linux engine first.'
}
& docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) {
    throw 'Docker engine unavailable. Open Docker Desktop and resolve its startup error. See docs/DEPLOYMENT.md for the recorded socket failure. No container has been deployed.'
}
$previousHostPort = $env:BATTERYTWIN_HOST_PORT
$env:BATTERYTWIN_HOST_PORT = "$Port"
try {
    & docker compose -f docker-compose.api.yml -p batterytwin-api config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration validation failed.' }
    & docker compose -f docker-compose.api.yml -p batterytwin-api up -d --build --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Docker build or container health check failed. Inspect: docker compose -f docker-compose.api.yml -p batterytwin-api logs' }
    $baseUrl = "http://127.0.0.1:$Port"
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 30
    if ($health.status -ne 'ready') { throw 'The container API did not report ready.' }
    $sample = Invoke-RestMethod -Uri "$baseUrl/api/batteries/B0006?through_cycle=60" -TimeoutSec 30
    $payload = @{ battery_id = $sample.battery_id; history = $sample.history } | ConvertTo-Json -Depth 6
    $result = Invoke-RestMethod -Uri "$baseUrl/api/analysis" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 60
    if ($null -eq $result.soh.predicted_soh) { throw 'Container prediction verification failed.' }
    $dashboard = Invoke-WebRequest -Uri $baseUrl -TimeoutSec 30
    if ($dashboard.StatusCode -ne 200) { throw 'Dashboard verification failed.' }
    Write-Host "Docker deployment verified: $baseUrl"
    Write-Host "API docs: $baseUrl/docs"
    Write-Host "B0006 cycle 61 SOH prediction: $($result.soh.predicted_soh)%"
    Write-Host 'View container: docker compose -f docker-compose.api.yml -p batterytwin-api ps'
    Write-Host 'Stop deployment: docker compose -f docker-compose.api.yml -p batterytwin-api down'
} finally {
    if ($null -eq $previousHostPort) {
        Remove-Item Env:BATTERYTWIN_HOST_PORT -ErrorAction SilentlyContinue
    } else {
        $env:BATTERYTWIN_HOST_PORT = $previousHostPort
    }
}
