from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote as urlquote

from app.net import lan_ip

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "housing.db"
CLIENT_SLUG = "chad-brizendine"
WEB_PORT = int(__import__("os").environ.get("HCC_PORT", "8787"))


app = FastAPI(title="Housing Command Center")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_client_id(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT id FROM clients WHERE slug = ?", (CLIENT_SLUG,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Client not found")
    return row["id"]


def today_briefing(conn: sqlite3.Connection, client_id: int):
    return conn.execute(
        """
        SELECT * FROM daily_briefings
        WHERE client_id = ? AND briefing_date = ?
        """,
        (client_id, date.today().isoformat()),
    ).fetchone()


@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse("/today", status_code=302)


@app.get("/connect", response_class=HTMLResponse)
async def connect_page(request: Request):
    ip = lan_ip()
    phone_url = f"http://{ip}:{WEB_PORT}/today" if ip else None
    qr_url = None
    if phone_url:
        qr_url = (
            "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
            + urlquote(phone_url, safe="")
        )
    return templates.TemplateResponse(
        request=request,
        name="connect.html",
        context={
            "phone_url": phone_url,
            "qr_url": qr_url,
            "local_url": f"http://127.0.0.1:{WEB_PORT}/today",
            "focus_count": None,
        },
    )


@app.get("/today", response_class=HTMLResponse)
async def today_page(request: Request):
    conn = db()
    try:
        client_id = get_client_id(conn)
        client = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        briefing = today_briefing(conn, client_id)
        tasks = []
        urgent = []
        if briefing:
            tasks = conn.execute(
                """
                SELECT t.*, p.name AS property_name
                FROM tasks t
                LEFT JOIN properties p ON p.id = t.property_id
                WHERE t.briefing_id = ?
                ORDER BY t.priority DESC, t.id
                """,
                (briefing["id"],),
            ).fetchall()
            urgent = json.loads(briefing["urgent_flags"] or "[]")

        pending_tasks = sum(1 for t in tasks if t["status"] == "pending")
        draft_count = conn.execute(
            """
            SELECT COUNT(*) FROM outreach_queue
            WHERE client_id = ? AND status = 'draft'
            """,
            (client_id,),
        ).fetchone()[0]

        focus_count = conn.execute(
            "SELECT COUNT(*) FROM client_waitlist_status WHERE client_id = ?",
            (client_id,),
        ).fetchone()[0]

        return templates.TemplateResponse(
            request=request,
            name="today.html",
            context={
                "client": client,
                "briefing": briefing,
                "tasks": tasks,
                "urgent": urgent,
                "pending_tasks": pending_tasks,
                "draft_count": draft_count,
                "focus_count": focus_count,
                "today": date.today().isoformat(),
            },
        )
    finally:
        conn.close()


@app.post("/tasks/{task_id}/done")
async def complete_task(task_id: int, notes: str = Form(default="")):
    conn = db()
    try:
        conn.execute(
            """
            UPDATE tasks SET
                status = 'done',
                completed_at = datetime('now'),
                completion_notes = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (notes.strip() or None, task_id),
        )
        conn.commit()
        row = conn.execute("SELECT briefing_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row and row["briefing_id"]:
            pending = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE briefing_id = ? AND status = 'pending'",
                (row["briefing_id"],),
            ).fetchone()[0]
            if pending == 0:
                conn.execute(
                    """
                    UPDATE daily_briefings SET status = 'completed', completed_at = datetime('now')
                    WHERE id = ?
                    """,
                    (row["briefing_id"],),
                )
                conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/today", status_code=303)


@app.get("/outreach", response_class=HTMLResponse)
async def outreach_page(request: Request, status: str = "draft"):
    conn = db()
    try:
        client_id = get_client_id(conn)
        rows = conn.execute(
            """
            SELECT oq.*, p.name AS property_name, p.phone, p.address, p.city, p.zip
            FROM outreach_queue oq
            LEFT JOIN properties p ON p.id = oq.property_id
            WHERE oq.client_id = ? AND oq.status = ?
            ORDER BY oq.priority DESC, oq.created_at DESC
            LIMIT 50
            """,
            (client_id, status),
        ).fetchall()
        counts = {
            s: conn.execute(
                "SELECT COUNT(*) FROM outreach_queue WHERE client_id = ? AND status = ?",
                (client_id, s),
            ).fetchone()[0]
            for s in ("draft", "approved", "sent")
        }
        focus_count = conn.execute(
            "SELECT COUNT(*) FROM client_waitlist_status WHERE client_id = ?",
            (client_id,),
        ).fetchone()[0]
        return templates.TemplateResponse(
            request=request,
            name="outreach.html",
            context={
                "items": rows,
                "status": status,
                "counts": counts,
                "focus_count": focus_count,
            },
        )
    finally:
        conn.close()


@app.get("/outreach/{item_id}", response_class=HTMLResponse)
async def outreach_detail(request: Request, item_id: int):
    conn = db()
    try:
        row = conn.execute(
            """
            SELECT oq.*, p.name AS property_name, p.phone, p.email AS property_email,
                   p.address, p.city, p.zip
            FROM outreach_queue oq
            LEFT JOIN properties p ON p.id = oq.property_id
            WHERE oq.id = ?
            """,
            (item_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404)
        focus_count = conn.execute(
            "SELECT COUNT(*) FROM client_waitlist_status WHERE client_id = ?",
            (row["client_id"],),
        ).fetchone()[0]
        return templates.TemplateResponse(
            request=request,
            name="outreach_detail.html",
            context={"item": row, "focus_count": focus_count},
        )
    finally:
        conn.close()


@app.post("/outreach/{item_id}/save")
async def save_outreach(item_id: int, recipient_email: str = Form(default="")):
    conn = db()
    try:
        email = recipient_email.strip() or None
        conn.execute(
            """
            UPDATE outreach_queue SET recipient_email = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (email, item_id),
        )
        if email:
            conn.execute(
                "UPDATE properties SET email = ?, updated_at = datetime('now') WHERE id = (SELECT property_id FROM outreach_queue WHERE id = ?)",
                (email, item_id),
            )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(f"/outreach/{item_id}", status_code=303)


@app.post("/outreach/{item_id}/approve")
async def approve_outreach(item_id: int, recipient_email: str = Form(default="")):
    conn = db()
    try:
        if recipient_email.strip():
            conn.execute(
                "UPDATE outreach_queue SET recipient_email = ? WHERE id = ?",
                (recipient_email.strip(), item_id),
            )
        conn.execute(
            """
            UPDATE outreach_queue SET status = 'approved', updated_at = datetime('now')
            WHERE id = ? AND status IN ('draft', 'failed')
            """,
            (item_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(f"/outreach/{item_id}", status_code=303)


@app.post("/outreach/{item_id}/send")
async def send_outreach(item_id: int):
    python = _python()
    script = ROOT / "scripts" / "send_one.py"
    subprocess.run(
        [python, str(script), str(item_id)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return RedirectResponse(f"/outreach/{item_id}", status_code=303)


@app.post("/outreach/send-approved")
async def send_all_approved():
    python = _python()
    script = ROOT / "scripts" / "send_approved.py"
    subprocess.Popen([python, str(script)], cwd=str(ROOT))
    return RedirectResponse("/outreach?status=approved", status_code=303)


@app.get("/properties", response_class=HTMLResponse)
async def properties_page(request: Request, q: str = ""):
    conn = db()
    try:
        client_id = get_client_id(conn)
        sql = """
            SELECT p.*, cws.status AS client_status, wp.status AS waitlist_status
            FROM client_waitlist_status cws
            JOIN properties p ON p.id = cws.property_id
            LEFT JOIN waitlist_profiles wp ON wp.property_id = p.id
            WHERE cws.client_id = ?
        """
        params: list = [client_id]
        if q.strip():
            sql += " AND (p.name LIKE ? OR p.address LIKE ? OR p.zip LIKE ? OR p.city LIKE ?)"
            like = f"%{q.strip()}%"
            params.extend([like, like, like, like])
        sql += " ORDER BY p.name LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        focus_count = conn.execute(
            "SELECT COUNT(*) FROM client_waitlist_status WHERE client_id = ?",
            (client_id,),
        ).fetchone()[0]
        return templates.TemplateResponse(
            request=request,
            name="properties.html",
            context={
                "properties": rows,
                "q": q,
                "focus_count": focus_count,
            },
        )
    finally:
        conn.close()


def _python() -> str:
    custom = Path(__file__).resolve().parents[1]
    venv_py = Path.home() / "agentic-ai" / "venv" / "bin" / "python3"
    return str(venv_py if venv_py.exists() else sys.executable)


@app.post("/run-daily")
async def trigger_daily():
    python = _python()
    script = ROOT / "scripts" / "run_daily.py"
    env = {**dict(__import__("os").environ), "HCC_LLM_ENABLED": "0"}
    subprocess.Popen(
        [python, str(script), "--force"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return RedirectResponse("/today", status_code=303)


@app.get("/manifest.json")
async def manifest():
    return RedirectResponse("/static/manifest.json", status_code=302)


from app.api_routes import router as api_router  # noqa: E402

app.include_router(api_router)