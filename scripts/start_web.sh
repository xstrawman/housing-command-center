#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${HCC_PYTHON:-$HOME/agentic-ai/venv/bin/python3}"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8787