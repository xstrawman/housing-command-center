#!/usr/bin/env python3
"""Batch-generate LLM outputs from pre-filled JSONL (outreach or synthetic)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

KIT = Path(__file__).resolve().parents[1]


def generate_one(
    base_url: str,
    model: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float = 0.3,
    system_prefix: str = "/no_think\n",
) -> str:
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": f"{system_prefix}{prompt}"}],
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        },
        timeout=600,
    )
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "").strip()
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input JSONL (outreach_batch.jsonl or synthetic_batch.jsonl)")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds between requests")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    out_path = args.out or args.input.with_name(args.input.stem + "_generated.jsonl")
    rows = load_jsonl(args.input)
    if args.start:
        rows = rows[args.start :]
    if args.limit:
        rows = rows[: args.limit]

    if args.dry_run:
        print(f"Would generate {len(rows)} records via {args.url} model={args.model}")
        print(f"Output → {out_path}")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    errors = 0

    with out_path.open("w", encoding="utf-8") as out_fh:
        for idx, row in enumerate(rows):
            prompt = row.get("prompt") or row.get("body_draft") or ""
            if not prompt:
                print(f"Skipping {row.get('id', idx)}: no prompt", file=sys.stderr)
                errors += 1
                continue
            try:
                output = generate_one(
                    args.url,
                    args.model,
                    prompt,
                    max_tokens=row.get("max_tokens", 600),
                    temperature=row.get("temperature", 0.3),
                )
                result = {**row, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "output": output}
                out_fh.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_fh.flush()
                done += 1
                if (done % 10) == 0:
                    print(f"  {done}/{len(rows)} …")
            except Exception as exc:
                errors += 1
                print(f"Error on {row.get('id', idx)}: {exc}", file=sys.stderr)
            if args.sleep:
                time.sleep(args.sleep)

    print(f"Generated {done}/{len(rows)} → {out_path} ({errors} errors)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())