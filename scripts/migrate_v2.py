#!/usr/bin/env python3
"""Add email fields for outreach sending."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "housing.db"

def main():
    conn = sqlite3.connect(DB)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(properties)")}
    if "email" not in cols:
        conn.execute("ALTER TABLE properties ADD COLUMN email TEXT")
    ocols = {r[1] for r in conn.execute("PRAGMA table_info(outreach_queue)")}
    if "recipient_email" not in ocols:
        conn.execute("ALTER TABLE outreach_queue ADD COLUMN recipient_email TEXT")
    conn.commit()
    conn.close()
    print("Migration v2 OK")

if __name__ == "__main__":
    main()