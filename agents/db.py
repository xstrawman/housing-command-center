from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any

from agents.config import DB_PATH


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_client(slug: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM clients WHERE slug = ?", (slug,)).fetchone()


def get_focus_filter() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT value FROM agent_config WHERE key = 'focus_filter'"
        ).fetchone()
    if not row:
        return {}
    return json.loads(row["value"])


def get_config_int(key: str, default: int) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT value FROM agent_config WHERE key = ?", (key,)
        ).fetchone()
    if not row:
        return default
    try:
        return int(row["value"])
    except ValueError:
        return default


def get_focus_properties(client_id: int, limit: int | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT p.*, cws.status AS client_status, cws.priority AS client_priority,
               wp.status AS waitlist_status, wp.next_follow_up_date,
               wp.estimated_next_open, wp.confidence_score
        FROM client_waitlist_status cws
        JOIN properties p ON p.id = cws.property_id
        LEFT JOIN waitlist_profiles wp ON wp.property_id = p.id
        WHERE cws.client_id = ?
        ORDER BY cws.priority DESC, p.name
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with connect() as conn:
        return conn.execute(sql, (client_id,)).fetchall()


def get_outreach_template(slug: str = "waitlist-intel-inquiry") -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM outreach_templates WHERE slug = ? AND is_active = 1",
            (slug,),
        ).fetchone()


def count_pending_outreach(client_id: int) -> int:
    with connect() as conn:
        return conn.execute(
            """
            SELECT COUNT(*) FROM outreach_queue
            WHERE client_id = ? AND status IN ('draft', 'approved', 'scheduled')
            """,
            (client_id,),
        ).fetchone()[0]


def log_agent_run(agent_name: str, status: str, summary: str, metadata: dict | None = None):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_runs (agent_name, status, finished_at, summary, metadata)
            VALUES (?, ?, datetime('now'), ?, ?)
            """,
            (agent_name, status, summary, json.dumps(metadata or {})),
        )


def briefing_exists(client_id: int, briefing_date: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM daily_briefings WHERE client_id = ? AND briefing_date = ?",
            (client_id, briefing_date),
        ).fetchone()
    return row is not None