from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from agents.config import BRIEFING_MINUTES
from agents.db import connect, get_focus_properties
from agents.llm import polish_text


def _needs_follow_up(prop: dict) -> bool:
    nfd = prop.get("next_follow_up_date")
    if not nfd:
        return True
    try:
        return datetime.fromisoformat(nfd).date() <= date.today()
    except ValueError:
        return True


def _opening_soon(prop: dict, lead_days: int) -> bool:
    est = prop.get("estimated_next_open")
    if not est:
        return False
    try:
        target = datetime.fromisoformat(est).date()
        return date.today() <= target <= date.today() + timedelta(days=lead_days)
    except ValueError:
        return False


def select_daily_priorities(
    client_id: int,
    *,
    max_tasks: int = 8,
    lead_days: int = 14,
) -> dict[str, Any]:
    props = [dict(r) for r in get_focus_properties(client_id)]
    partial = [p for p in props if p.get("data_quality") == "partial"]
    unknown = [p for p in props if p.get("waitlist_status") in (None, "unknown")]
    follow_up = [p for p in props if _needs_follow_up(p)]
    opening = [p for p in props if _opening_soon(p, lead_days)]

    # Score: partial data + unknown waitlist + due follow-up
    scored: list[tuple[float, dict]] = []
    for p in props:
        score = float(p.get("client_priority") or 50)
        if p.get("data_quality") == "partial":
            score += 20
        if p.get("waitlist_status") in (None, "unknown"):
            score += 15
        if _needs_follow_up(p):
            score += 10
        if _opening_soon(p, lead_days):
            score += 25
        scored.append((score, p))

    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
    top = [p for _, p in scored[:max_tasks]]

    tasks: list[dict] = []
    for p in top[:3]:
        if p.get("phone"):
            tasks.append({
                "title": f"Call {p['name']}",
                "description": (
                    f"Ask if waitlist is open. Phone: {p['phone']}. "
                    f"Address: {p.get('address', '')}, {p.get('city', '')} {p.get('zip', '')}"
                ),
                "task_type": "call",
                "property_id": p["id"],
                "estimated_minutes": 3,
                "priority": 90,
            })

    for p in top[3:6]:
        tasks.append({
            "title": f"Review outreach draft for {p['name']}",
            "description": "Approve or edit the agent-drafted waitlist inquiry email.",
            "task_type": "email",
            "property_id": p["id"],
            "estimated_minutes": 2,
            "priority": 70,
        })

    if partial:
        tasks.append({
            "title": f"Research gaps on {partial[0]['name']}",
            "description": "Partial listing — confirm bedrooms, rent, and waitlist status.",
            "task_type": "research",
            "property_id": partial[0]["id"],
            "estimated_minutes": 3,
            "priority": 60,
        })

    tasks.append({
        "title": "Check DHA website for waitlist announcements",
        "description": "https://www.denverhousing.org — look for open application windows.",
        "task_type": "research",
        "property_id": None,
        "estimated_minutes": 3,
        "priority": 80,
    })

    urgent = []
    if opening:
        urgent.append(f"{len(opening)} properties may open within {lead_days} days")
    if len(unknown) > 100:
        urgent.append(f"{len(unknown)} properties still have unknown waitlist status")

    summary_lines = [
        f"Focus area: {len(props)} properties (80203 + west corridor).",
        f"Unknown waitlists: {len(unknown)}. Partial records: {len(partial)}.",
        f"Due for follow-up: {len(follow_up)}.",
        f"Today's plan: {len(tasks)} tasks, ~{BRIEFING_MINUTES} minutes.",
    ]

    summary = "\n".join(summary_lines)
    polished = polish_text(
        "Rewrite this housing briefing summary in 3 short, direct sentences for Chad:\n"
        + summary
    )
    if polished:
        summary = polished

    return {
        "property_count": len(props),
        "unknown_count": len(unknown),
        "partial_count": len(partial),
        "follow_up_count": len(follow_up),
        "opening_soon_count": len(opening),
        "tasks": tasks[:max_tasks],
        "summary": summary,
        "urgent_flags": urgent,
    }


def write_briefing(client_id: int, analysis: dict[str, Any], briefing_date: str | None = None) -> int:
    briefing_date = briefing_date or date.today().isoformat()
    title = f"Daily Briefing — {briefing_date}"

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_briefings (
                client_id, briefing_date, title, summary, urgent_flags,
                estimated_minutes, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(client_id, briefing_date) DO UPDATE SET
                title = excluded.title,
                summary = excluded.summary,
                urgent_flags = excluded.urgent_flags,
                estimated_minutes = excluded.estimated_minutes,
                status = 'pending'
            """,
            (
                client_id,
                briefing_date,
                title,
                analysis["summary"],
                json.dumps(analysis.get("urgent_flags", [])),
                BRIEFING_MINUTES,
            ),
        )
        briefing_id = conn.execute(
            "SELECT id FROM daily_briefings WHERE client_id = ? AND briefing_date = ?",
            (client_id, briefing_date),
        ).fetchone()[0]

        conn.execute(
            "DELETE FROM tasks WHERE client_id = ? AND briefing_id = ?",
            (client_id, briefing_id),
        )
        for task in analysis["tasks"]:
            conn.execute(
                """
                INSERT INTO tasks (
                    client_id, briefing_id, property_id, title, description,
                    task_type, priority, status, estimated_minutes, due_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    client_id,
                    briefing_id,
                    task.get("property_id"),
                    task["title"],
                    task["description"],
                    task["task_type"],
                    task.get("priority", 50),
                    task.get("estimated_minutes"),
                    briefing_date,
                ),
            )

    return briefing_id