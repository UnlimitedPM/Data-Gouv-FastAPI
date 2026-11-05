# Ouvre le backend et le frontend dans deux fenetres PowerShell.
$ErrorActionPreference = "Stop"

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "scripts\run_backend.ps1")
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "scripts\run_frontend.ps1")

Write-Host "Backend : http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend : http://127.0.0.1:8501" -ForegroundColor Cyan
