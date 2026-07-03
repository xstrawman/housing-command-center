from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "housing.db"
CLIENT_SLUG = "chad-brizendine"
WEB_PORT = int(__import__("os").environ.get("HCC_PORT", "8787"))


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_client_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM clients WHERE slug = ?", (CLIENT_SLUG,)).fetchone()
    if not row:
        raise HTTPException(404, "Client not found")
    return row["id"]


def today_briefing(conn: sqlite3.Connection, client_id: int):
    return conn.execute(
        "SELECT * FROM daily_briefings WHERE client_id = ? AND briefing_date = ?",
        (client_id, date.today().isoformat()),
    ).fetchone()


from app.net import lan_ip  # noqa: F401

router = APIRouter(prefix="/api")


def _rows_to_dicts(rows):
    return [dict(r) for r in rows]


@router.get("/health")
def health():
    return {
        "ok": True,
        "date": date.today().isoformat(),
        "lan_ip": lan_ip(),
        "port": WEB_PORT,
    }


@router.get("/briefing/today")
def api_briefing_today():
    conn = db()
    try:
        client_id = get_client_id(conn)
        briefing = today_briefing(conn, client_id)
        if not briefing:
            return {"briefing": None, "tasks": [], "urgent": []}
        tasks = conn.execute(
            """
            SELECT t.*, p.name AS property_name, p.phone
            FROM tasks t
            LEFT JOIN properties p ON p.id = t.property_id
            WHERE t.briefing_id = ?
            ORDER BY t.priority DESC, t.id
            """,
            (briefing["id"],),
        ).fetchall()
        return {
            "briefing": dict(briefing),
            "urgent": json.loads(briefing["urgent_flags"] or "[]"),
            "tasks": _rows_to_dicts(tasks),
        }
    finally:
        conn.close()


class TaskDoneBody(BaseModel):
    notes: str = ""


@router.post("/tasks/{task_id}/done")
def api_task_done(task_id: int, body: TaskDoneBody | None = None):
    notes = (body.notes if body else "") or ""
    conn = db()
    try:
        conn.execute(
            """
            UPDATE tasks SET status='done', completed_at=datetime('now'),
                completion_notes=?, updated_at=datetime('now')
            WHERE id = ?
            """,
            (notes.strip() or None, task_id),
        )
        conn.commit()
        if conn.total_changes == 0:
            raise HTTPException(404, "Task not found")
        return {"ok": True, "task_id": task_id}
    finally:
        conn.close()


@router.get("/outreach")
def api_outreach(status: str = "draft", limit: int = 20):
    conn = db()
    try:
        client_id = get_client_id(conn)
        rows = conn.execute(
            """
            SELECT oq.id, oq.subject, oq.status, oq.body, oq.created_at,
                   p.name AS property_name, p.phone, p.city, p.zip
            FROM outreach_queue oq
            LEFT JOIN properties p ON p.id = oq.property_id
            WHERE oq.client_id = ? AND oq.status = ?
            ORDER BY oq.priority DESC LIMIT ?
            """,
            (client_id, status, limit),
        ).fetchall()
        return {"items": _rows_to_dicts(rows)}
    finally:
        conn.close()


@router.post("/outreach/{item_id}/approve")
def api_outreach_approve(item_id: int):
    conn = db()
    try:
        conn.execute(
            "UPDATE outreach_queue SET status='approved', updated_at=datetime('now') WHERE id=? AND status='draft'",
            (item_id,),
        )
        conn.commit()
        return {"ok": True, "id": item_id}
    finally:
        conn.close()