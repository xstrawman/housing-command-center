from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from agents.config import DAILY_EMAIL_CAP
from agents.db import connect, get_config_int

HIMALAYA = "himalaya"
ACCOUNT = "yahoo"


def _build_mml(to_addr: str, subject: str, body: str, from_name: str, from_email: str) -> str:
    # Strip property header block for outbound — keep questions only
    lines = body.splitlines()
    out_lines: list[str] = []
    skip_header = True
    for line in lines:
        if skip_header and (line.startswith("Property:") or line.startswith("Address:") or line.startswith("Phone on file:")):
            continue
        if skip_header and line.strip() == "":
            continue
        skip_header = False
        out_lines.append(line)
    clean_body = "\n".join(out_lines).strip() or body

    return (
        f"From: {from_name} <{from_email}>\n"
        f"To: {to_addr}\n"
        f"Subject: {subject}\n"
        "\n"
        f"{clean_body}\n"
    )


def send_via_himalaya(mml: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".mml", delete=False) as f:
        f.write(mml)
        path = f.name
    try:
        result = subprocess.run(
            [HIMALAYA, "template", "send", "-a", ACCOUNT, path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True, (result.stdout or "sent").strip()
        return False, (result.stderr or result.stdout or "send failed").strip()
    finally:
        Path(path).unlink(missing_ok=True)


def send_approved_batch(
    client_id: int,
    *,
    limit: int | None = None,
    queue_ids: list[int] | None = None,
) -> list[dict]:
    cap = limit or min(DAILY_EMAIL_CAP, get_config_int("daily_email_cap", DAILY_EMAIL_CAP))
    client = None
    results: list[dict] = []

    with connect() as conn:
        client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not client:
            return results

        if queue_ids:
            placeholders = ",".join("?" * len(queue_ids))
            rows = conn.execute(
                f"""
                SELECT oq.*, p.email AS property_email
                FROM outreach_queue oq
                LEFT JOIN properties p ON p.id = oq.property_id
                WHERE oq.client_id = ? AND oq.id IN ({placeholders})
                  AND oq.status IN ('approved', 'draft') AND oq.channel = 'email'
                """,
                [client_id, *queue_ids],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT oq.*, p.email AS property_email
                FROM outreach_queue oq
                LEFT JOIN properties p ON p.id = oq.property_id
                WHERE oq.client_id = ? AND oq.status = 'approved' AND oq.channel = 'email'
                ORDER BY oq.priority DESC
                LIMIT ?
                """,
                (client_id, cap),
            ).fetchall()

        sent_today = conn.execute(
            """
            SELECT COUNT(*) FROM outreach_queue
            WHERE client_id = ? AND status = 'sent' AND date(sent_at) = date('now')
            """,
            (client_id,),
        ).fetchone()[0]

        remaining = max(0, cap - sent_today)

        for row in rows:
            if remaining <= 0:
                break
            to_addr = row["recipient_email"] or row["property_email"]
            if not to_addr or "@" not in to_addr:
                results.append({
                    "id": row["id"],
                    "ok": False,
                    "error": "missing recipient email — add on Outreach page after calling property",
                })
                conn.execute(
                    """
                    UPDATE outreach_queue SET error_message = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    ("missing recipient email", row["id"]),
                )
                continue

            mml = _build_mml(
                to_addr,
                row["subject"],
                row["body"],
                client["full_name"],
                client["email"],
            )
            ok, msg = send_via_himalaya(mml)
            if ok:
                remaining -= 1
                conn.execute(
                    """
                    UPDATE outreach_queue SET
                        status = 'sent', sent_at = datetime('now'),
                        error_message = NULL, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (row["id"],),
                )
                conn.execute(
                    """
                    INSERT INTO outreach_log (queue_id, property_id, client_id, channel, subject, body, sent_at)
                    VALUES (?, ?, ?, 'email', ?, ?, datetime('now'))
                    """,
                    (row["id"], row["property_id"], client_id, row["subject"], row["body"]),
                )
            else:
                conn.execute(
                    """
                    UPDATE outreach_queue SET status = 'failed', error_message = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (msg[:500], row["id"]),
                )
            results.append({"id": row["id"], "ok": ok, "to": to_addr, "error": None if ok else msg})

    return results