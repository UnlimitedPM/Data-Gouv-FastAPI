# Demarre l'API FastAPI sur http://127.0.0.1:8000
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Environnement introuvable. Lancez d'abord scripts\setup.ps1."
}

Set-Location (Join-Path $root "backend")
& $python -m uvicorn app.main:app --reload --port 8000
