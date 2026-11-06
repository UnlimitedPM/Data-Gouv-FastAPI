# Cree l'environnement virtuel et installe les dependances du projet.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Creation de l'environnement virtuel Python 3.11..." -ForegroundColor Cyan
    py -3.11 -m venv (Join-Path $root ".venv")
}

Write-Host "Installation des dependances backend..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root "backend\requirements.txt")

Write-Host "Installation des dependances frontend..." -ForegroundColor Cyan
& $python -m pip install -r (Join-Path $root "frontend\requirements.txt")

if (-not (Test-Path (Join-Path $root "backend\.env"))) {
    Copy-Item (Join-Path $root "backend\.env.example") (Join-Path $root "backend\.env")
    Write-Host "Fichier backend/.env cree a partir de .env.example." -ForegroundColor Green
}

Write-Host "Termine." -ForegroundColor Green
Write-Host "Etape suivante (une fois) : cd backend; python -m app.ingest" -ForegroundColor Yellow
Write-Host "Puis lancez scripts\run_backend.ps1 et scripts\run_frontend.ps1." -ForegroundColor Green
