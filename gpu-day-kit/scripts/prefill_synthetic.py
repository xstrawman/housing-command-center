#!/usr/bin/env python3
"""Pre-fill synthetic email-reply generation prompts for GPU batch work."""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.config import CLIENT_SLUG  # noqa: E402
from agents.db import get_client, get_focus_properties  # noqa: E402

KIT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = KIT / "prompts" / "synthetic_email_reply.txt"
DEFAULT_OUT = KIT / "exports" / "synthetic_batch.jsonl"

TONES = ["helpful", "terse", "redirect", "voicemail_style", "auto_reply", "out_of_office"]


def render_template(template: str, prop: dict, tone: str) -> str:
    return (
        template.replace("{{tone}}", tone)
        .replace("{{property_name}}", prop.get("name") or "Unknown Property")
        .replace("{{address}}", prop.get("address") or "")
        .replace("{{city}}", prop.get("city") or "Denver")
        .replace("{{zip}}", prop.get("zip") or "")
        .replace("{{phone}}", prop.get("phone") or "unknown")
        .replace("{{property_type}}", prop.get("property_type") or "Family")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--client", default=CLIENT_SLUG)
    args = parser.parse_args()

    client = get_client(args.client)
    if not client:
        print(f"Client not found: {args.client}", file=sys.stderr)
        return 1

    props = [dict(r) for r in get_focus_properties(client["id"])]
    if not props:
        print("No focus properties found", file=sys.stderr)
        return 1

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rng = random.Random(args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for i in range(args.count):
            prop = props[i % len(props)]
            tone = TONES[i % len(TONES)]
            prompt = render_template(template, prop, tone)
            record = {
                "id": f"synth-email-{i + 1:05d}",
                "property_id": prop["id"],
                "property_name": prop.get("name"),
                "tone": tone,
                "prompt": prompt,
                "task": "synthetic_email_reply",
                "max_tokens": 900,
                "temperature": 0.7,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": date.today().isoformat(),
        "count": args.count,
        "unique_properties": len(props),
        "seed": args.seed,
        "output": str(args.out),
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {args.count} synthetic prompts → {args.out}")
    print(f"  cycling {len(props)} properties × {len(TONES)} tones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())