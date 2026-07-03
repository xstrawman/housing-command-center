from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("HCC_DB", ROOT / "db" / "housing.db"))
CLIENT_SLUG = os.environ.get("HCC_CLIENT", "chad-brizendine")

OLLAMA_BASE_URL = os.environ.get("HCC_LLM_URL", "http://127.0.0.1:11435")
OLLAMA_MODEL = os.environ.get("HCC_LLM_MODEL", "Qwen3-8B-int4-cw")
LLM_ENABLED = os.environ.get("HCC_LLM_ENABLED", "1") == "1"

DAILY_EMAIL_CAP = 5
BRIEFING_MINUTES = 15
OUTREACH_BATCH_SIZE = 5