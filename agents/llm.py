from __future__ import annotations

import logging

import requests

from agents.config import LLM_ENABLED, OLLAMA_BASE_URL, OLLAMA_MODEL

log = logging.getLogger(__name__)


def polish_text(prompt: str, max_tokens: int = 400) -> str | None:
    """Optional LLM polish. Returns None if unavailable or empty."""
    if not LLM_ENABLED:
        return None
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": f"/no_think\n{prompt}",
                    }
                ],
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        if not content or content.startswith("<think>"):
            return None
        return content
    except Exception as exc:
        log.warning("LLM unavailable: %s", exc)
        return None