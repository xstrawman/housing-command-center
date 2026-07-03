#!/usr/bin/env python3
"""Pre-fill outreach batch JSON for GPU batch generation."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.config import CLIENT_SLUG  # noqa: E402
from agents.db import connect, get_client, get_focus_properties, get_outreach_template  # noqa: E402
from agents.outreach import _personalize_body, select_outreach_targets  # noqa: E402

KIT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = KIT / "exports" / "outreach_batch.jsonl"


def build_record(prop: dict, client: dict, template: dict, *, mode: str) -> dict:
    body = _personalize_body(template["body"], prop, client)
    subject = f"Waitlist inquiry — {prop.get('name', 'affordable housing')}"
    record = {
        "id": f"outreach-{prop['id']}",
        "property_id": prop["id"],
        "property_name": prop.get("name"),
        "address": prop.get("address"),
        "city": prop.get("city"),
        "zip": prop.get("zip"),
        "phone": prop.get("phone"),
        "waitlist_status": prop.get("waitlist_status"),
        "data_quality": prop.get("data_quality"),
        "client_priority": prop.get("client_priority"),
        "subject": subject,
        "body_draft": body,
        "template_slug": template["slug"],
        "scheduled_for": date.today().isoformat(),
    }
    if mode == "polish":
        record["prompt"] = (
            "Tighten this outreach email (keep all questions, stay professional):\n\n"
            + body[:2000]
        )
        record["task"] = "outreach_polish"
        record["max_tokens"] = 600
    elif mode == "full":
        record["prompt"] = body
        record["task"] = "outreach_draft"
        record["max_tokens"] = 800
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("polish", "full", "all"),
        default="polish",
        help="polish=agent LLM step; full=all targets; all=entire focus list",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max records (0=all)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--client", default=CLIENT_SLUG)
    args = parser.parse_args()

    client_row = get_client(args.client)
    if not client_row:
        print(f"Client not found: {args.client}", file=sys.stderr)
        return 1

    client = dict(client_row)
    client_id = client["id"]
    template = get_outreach_template("waitlist-intel-inquiry")
    if not template:
        print("Outreach template waitlist-intel-inquiry not found", file=sys.stderr)
        return 1
    template = dict(template)

    if args.mode == "all":
        props = [dict(r) for r in get_focus_properties(client_id)]
        mode = "polish"
    elif args.mode == "full":
        props = select_outreach_targets(client_id, batch_size=9999)
        mode = "polish"
    else:
        props = select_outreach_targets(client_id, batch_size=args.limit or 218)
        mode = args.mode

    if args.limit and args.mode != "all":
        props = props[: args.limit]

    # Skip properties already in outreach queue
    with connect() as conn:
        queued = {
            r[0]
            for r in conn.execute(
                """
                SELECT property_id FROM outreach_queue
                WHERE client_id = ? AND status IN ('draft', 'approved', 'scheduled', 'sent')
                """,
                (client_id,),
            ).fetchall()
        }

    records = []
    for prop in props:
        if prop["id"] in queued and args.mode != "all":
            continue
        records.append(build_record(prop, client, template, mode=mode))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    meta = {
        "generated_at": date.today().isoformat(),
        "client": args.client,
        "mode": args.mode,
        "count": len(records),
        "output": str(args.out),
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {len(records)} outreach records → {args.out}")
    print(f"Meta: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())