from __future__ import annotations

from datetime import date

from agents.config import DAILY_EMAIL_CAP, OUTREACH_BATCH_SIZE
from agents.db import connect, count_pending_outreach, get_focus_properties, get_outreach_template
from agents.llm import polish_text


def _personalize_body(template_body: str, prop: dict, client: dict) -> str:
    header = (
        f"Property: {prop.get('name', 'Unknown')}\n"
        f"Address: {prop.get('address', '')}, {prop.get('city', '')} {prop.get('zip', '')}\n"
        f"Phone on file: {prop.get('phone') or 'unknown'}\n\n"
    )
    body = template_body.replace(
        "Chad Brizendine",
        client.get("full_name", "Chad Brizendine"),
    )
    if prop.get("name"):
        body = body.replace(
            "your waitlist",
            f"the waitlist at {prop['name']}",
            1,
        )
    return header + body


def select_outreach_targets(client_id: int, batch_size: int = OUTREACH_BATCH_SIZE) -> list[dict]:
    props = [dict(r) for r in get_focus_properties(client_id)]
    candidates = [
        p for p in props
        if p.get("waitlist_status") in (None, "unknown", "closed")
        and not _already_queued(client_id, p["id"])
    ]
    candidates.sort(
        key=lambda p: (
            0 if p.get("data_quality") == "partial" else 1,
            -(p.get("client_priority") or 50),
            p.get("name", ""),
        )
    )
    return candidates[:batch_size]


def _already_queued(client_id: int, property_id: int) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM outreach_queue
            WHERE client_id = ? AND property_id = ?
              AND status IN ('draft', 'approved', 'scheduled', 'sent')
            """,
            (client_id, property_id),
        ).fetchone()
    return row is not None


def draft_outreach_batch(client_id: int, client: dict, template_slug: str = "waitlist-intel-inquiry") -> list[int]:
    cap = min(DAILY_EMAIL_CAP, OUTREACH_BATCH_SIZE)
    pending = count_pending_outreach(client_id)
    if pending >= DAILY_EMAIL_CAP:
        return []

    template = get_outreach_template(template_slug)
    if not template:
        return []

    targets = select_outreach_targets(client_id, batch_size=cap)
    queue_ids: list[int] = []

    with connect() as conn:
        for prop in targets:
            body = _personalize_body(template["body"], prop, client)
            polished = polish_text(
                f"Tighten this outreach email (keep all questions, stay professional):\n\n{body[:2000]}"
            )
            if polished and len(polished) > 100:
                body = polished

            subject = f"Waitlist inquiry — {prop.get('name', 'affordable housing')}"
            cur = conn.execute(
                """
                INSERT INTO outreach_queue (
                    client_id, property_id, template_id, channel, subject, body,
                    status, priority, scheduled_for
                ) VALUES (?, ?, ?, 'email', ?, ?, 'draft', ?, ?)
                """,
                (
                    client_id,
                    prop["id"],
                    template["id"],
                    subject,
                    body,
                    prop.get("client_priority") or 50,
                    date.today().isoformat(),
                ),
            )
            queue_ids.append(cur.lastrowid)

            conn.execute(
                """
                UPDATE waitlist_profiles SET
                    next_follow_up_date = date('now', '+90 days'),
                    updated_at = datetime('now')
                WHERE property_id = ?
                """,
                (prop["id"],),
            )

    return queue_ids