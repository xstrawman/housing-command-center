#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.db import connect
from agents.sender import send_approved_batch

def main():
    if len(sys.argv) < 2:
        return 1
    item_id = int(sys.argv[1])
    with connect() as conn:
        row = conn.execute("SELECT client_id FROM outreach_queue WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return 1
        client_id = row["client_id"]
        conn.execute(
            "UPDATE outreach_queue SET status = 'approved' WHERE id = ? AND status IN ('draft', 'failed')",
            (item_id,),
        )
    send_approved_batch(client_id, queue_ids=[item_id], limit=1)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())