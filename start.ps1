$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Create .venv and install requirements first; see README.md.' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    Push-Location frontend
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard dependency installation failed.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed.' }
    Pop-Location
}
Write-Host 'BatteryTwin dashboard: http://127.0.0.1:8000'
& .venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
