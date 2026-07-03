#!/usr/bin/env python3
"""Export Housing Command Center data bundle for GPU day work."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "db" / "housing.db"
DEFAULT_EXPORTS = KIT / "exports"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def export_json(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=None, help="Export directory (default: exports/<timestamp>)")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Database not found: {args.db}", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or (DEFAULT_EXPORTS / stamp)
    out_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(args.db, out_dir / "housing.db")

    with connect(args.db) as conn:
        client = conn.execute("SELECT * FROM clients WHERE slug = 'chad-brizendine'").fetchone()
        client_id = client["id"] if client else 1

        focus_props = export_json(
            conn,
            """
            SELECT p.*, cws.status AS client_status, cws.priority AS client_priority,
                   wp.status AS waitlist_status, wp.next_follow_up_date,
                   wp.estimated_next_open, wp.confidence_score
            FROM client_waitlist_status cws
            JOIN properties p ON p.id = cws.property_id
            LEFT JOIN waitlist_profiles wp ON wp.property_id = p.id
            WHERE cws.client_id = ?
            ORDER BY cws.priority DESC, p.name
            """,
            (client_id,),
        )

        bundle = {
            "exported_at": stamp,
            "client": dict(client) if client else None,
            "agent_config": {
                row["key"]: json.loads(row["value"]) if row["key"] == "focus_filter" else row["value"]
                for row in conn.execute("SELECT key, value FROM agent_config")
            },
            "counts": {
                "properties_total": conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0],
                "focus_properties": len(focus_props),
                "housing_authorities": conn.execute("SELECT COUNT(*) FROM housing_authorities").fetchone()[0],
                "outreach_templates": conn.execute(
                    "SELECT COUNT(*) FROM outreach_templates WHERE is_active = 1"
                ).fetchone()[0],
                "outreach_queue": conn.execute("SELECT COUNT(*) FROM outreach_queue").fetchone()[0],
            },
        }

        (out_dir / "manifest.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        (out_dir / "focus_properties.json").write_text(
            json.dumps(focus_props, indent=2), encoding="utf-8"
        )
        (out_dir / "outreach_templates.json").write_text(
            json.dumps(
                export_json(conn, "SELECT * FROM outreach_templates WHERE is_active = 1"),
                indent=2,
            ),
            encoding="utf-8",
        )
        (out_dir / "housing_authorities.json").write_text(
            json.dumps(export_json(conn, "SELECT * FROM housing_authorities ORDER BY name"), indent=2),
            encoding="utf-8",
        )

        if (row := conn.execute("SELECT value FROM agent_config WHERE key = 'focus_filter'").fetchone()):
            (out_dir / "focus_filter.json").write_text(row["value"], encoding="utf-8")

    # Copy prompt/schema assets into bundle
    for sub in ("prompts", "schemas"):
        src = KIT / sub
        if src.exists():
            shutil.copytree(src, out_dir / sub, dirs_exist_ok=True)

    print(f"Exported to {out_dir}")
    print(f"  focus properties: {bundle['counts']['focus_properties']}")
    print(f"  manifest:         {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())