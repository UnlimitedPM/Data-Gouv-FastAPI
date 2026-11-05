# Demarre le frontend Streamlit sur http://127.0.0.1:8501
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Environnement introuvable. Lancez d'abord scripts\setup.ps1."
}

$env:API_URL = "http://127.0.0.1:8000"
Set-Location (Join-Path $root "frontend")
& $python -m streamlit run app.py --server.port 8501
