#!/usr/bin/env python3
"""Display today's briefing and pending outreach drafts."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "housing.db"


def main() -> int:
    today = date.today().isoformat()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    briefing = conn.execute(
        """
        SELECT * FROM daily_briefings
        WHERE briefing_date = ?
        ORDER BY id DESC LIMIT 1
        """,
        (today,),
    ).fetchone()

    if not briefing:
        print(f"No briefing for {today}. Run: python3 scripts/run_daily.py")
        return 1

    print(f"# {briefing['title']}\n")
    print(briefing["summary"])
    urgent = json.loads(briefing["urgent_flags"] or "[]")
    if urgent:
        print("\n## Urgent\n")
        for u in urgent:
            print(f"- {u}")

    tasks = conn.execute(
        """
        SELECT title, description, task_type, estimated_minutes, status
        FROM tasks WHERE briefing_id = ? ORDER BY priority DESC
        """,
        (briefing["id"],),
    ).fetchall()
    print(f"\n## Tasks ({len(tasks)})\n")
    for i, t in enumerate(tasks, 1):
        print(f"{i}. **{t['title']}** ({t['estimated_minutes']}m, {t['task_type']})")
        if t["description"]:
            print(f"   {t['description'][:120]}")

    drafts = conn.execute(
        """
        SELECT oq.subject, p.name, oq.status
        FROM outreach_queue oq
        LEFT JOIN properties p ON p.id = oq.property_id
        WHERE oq.status = 'draft' AND date(oq.created_at) = date('now')
        ORDER BY oq.priority DESC LIMIT 10
        """
    ).fetchall()
    print(f"\n## Outreach drafts today ({len(drafts)})\n")
    for d in drafts:
        print(f"- {d['name']}: {d['subject']}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())