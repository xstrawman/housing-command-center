#!/usr/bin/env python3
"""Run the daily housing agent pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.graph import run_daily_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Housing Command Center daily agents")
    parser.add_argument("--force", action="store_true", help="Regenerate today's briefing")
    parser.add_argument("--date", help="Briefing date YYYY-MM-DD (default: today)")
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    args = parser.parse_args()

    result = run_daily_pipeline(force=args.force, briefing_date=args.date)

    if args.json:
        print(json.dumps({
            "status": result.get("status"),
            "briefing_id": result.get("briefing_id"),
            "tasks": len(result.get("analysis", {}).get("tasks", [])),
            "outreach_drafts": len(result.get("outreach_ids", [])),
            "errors": result.get("errors", []),
            "summary": result.get("analysis", {}).get("summary"),
        }, indent=2))
        return 0 if result.get("status") == "success" else 1

    print("=" * 60)
    print("HOUSING COMMAND CENTER — DAILY BRIEFING")
    print("=" * 60)
    if result.get("analysis"):
        print(result["analysis"]["summary"])
        print()
        urgent = result["analysis"].get("urgent_flags", [])
        if urgent:
            print("URGENT:")
            for flag in urgent:
                print(f"  ! {flag}")
            print()
        print("TODAY'S TASKS:")
        for i, task in enumerate(result["analysis"].get("tasks", []), 1):
            mins = task.get("estimated_minutes", "?")
            print(f"  {i}. [{mins}m] {task['title']}")
            if task.get("description"):
                print(f"     {task['description'][:100]}")
        print()
    print(f"Outreach drafts queued: {len(result.get('outreach_ids', []))}")
    if result.get("errors"):
        print("Errors:", "; ".join(result["errors"]))
        return 1
    print(f"Briefing ID: {result.get('briefing_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())