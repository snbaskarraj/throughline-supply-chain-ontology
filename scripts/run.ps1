# One-shot setup + test + run (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv)) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
python -m pytest -q
$env:PYTHONPATH = "src"
Write-Host "Open http://localhost:8000  (API docs: http://localhost:8000/docs)"
uvicorn throughline.api:app --reload --port 8000
