#!/usr/bin/env bash
# One-shot setup + test + run (macOS / Linux / Git Bash)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
[ -d .venv ] || $PY -m venv .venv
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; else source .venv/Scripts/activate; fi
pip install -q -r requirements.txt
python -m pytest -q
echo "Open http://localhost:8000  (API docs: http://localhost:8000/docs)"
PYTHONPATH=src uvicorn throughline.api:app --reload --port 8000
