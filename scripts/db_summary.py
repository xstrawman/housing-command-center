#!/usr/bin/env python3
"""Print a quick summary of the housing database."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "housing.db"


def main() -> None:
    if not DB.exists():
        print(f"No database at {DB}. Run: python scripts/seed_from_pdf.py")
        return

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    def count(table: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    print(f"=== Housing Command Center — {DB} ===\n")
    print(f"Clients:              {count('clients')}")
    print(f"Properties:           {count('properties')}")
    print(f"Waitlist profiles:    {count('waitlist_profiles')}")
    print(f"Housing authorities:  {count('housing_authorities')}")
    print(f"Outreach templates:   {count('outreach_templates')}")
    print(f"Documents:            {count('documents')}")

    print("\nProperties by county:")
    for row in conn.execute(
        """
        SELECT county, COUNT(*) AS n,
               SUM(CASE WHEN data_quality = 'complete' THEN 1 ELSE 0 END) AS complete
        FROM properties GROUP BY county ORDER BY n DESC
        """
    ):
        print(f"  {row['county'] or 'Unknown':20} {row['n']:4}  ({row['complete']} complete)")

    print("\nHousing authorities:")
    for row in conn.execute(
        "SELECT name, website FROM housing_authorities ORDER BY name"
    ):
        print(f"  {row['name']:18} {row['website']}")

    client = conn.execute(
        """
        SELECT c.full_name, c.email, cr.target_counties
        FROM clients c
        LEFT JOIN client_requirements cr ON cr.client_id = c.id
        LIMIT 1
        """
    ).fetchone()
    if client:
        print(f"\nClient #1: {client['full_name']} ({client['email']})")
        print(f"  Target counties: {client['target_counties']}")

    conn.close()


if __name__ == "__main__":
    main()