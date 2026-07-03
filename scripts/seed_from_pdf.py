#!/usr/bin/env python3
"""Parse the Affordable Housing List PDF and seed the database."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "housing.db"
PDF_PATH = Path("/home/mountaindewurbest/Downloads/Affordable Housing LIst.pdf")
SCHEMA_PATH = ROOT / "db" / "schema.sql"

HEADER_WORDS = {
    "city", "zip", "phone", "number", "type", "units", "bed",
    "lihtc property list", "01/17.v3", "# of",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def property_key(name: str, address: str, zip_code: str) -> str:
    raw = f"{name}|{address}|{zip_code}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def extract_pdf_text(pdf_path: Path) -> list[str]:
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines()]


def is_county_header(line: str) -> bool:
    if line == "HOUSING AUTHORITIES":
        return True
    low = line.lower()
    if not low.endswith(" county"):
        return False
    # Avoid addresses like "3210 East County" (County Line Road)
    return not re.match(r"^\d", line)


def normalize_county(line: str) -> str:
    return line.replace(" county", "").replace(" COUNTY", "").strip().title()


def nonempty_after(lines: list[str], idx: int, count: int = 2) -> list[str]:
    out: list[str] = []
    j = idx + 1
    while j < len(lines) and len(out) < count:
        if lines[j]:
            out.append(lines[j])
        j += 1
    return out


def prev_record_stop(lines: list[str], idx: int) -> int:
    for j in range(idx - 1, -1, -1):
        if lines[j] in ("Family", "Senior"):
            seen = 0
            for k in range(j + 1, idx):
                if lines[k]:
                    seen += 1
                    if seen >= 2:
                        return k
            return j
    return -1


def nonempty_before(lines: list[str], idx: int, stop_at: int = -1) -> list[str]:
    out: list[str] = []
    j = idx - 1
    while j > stop_at:
        if lines[j]:
            if lines[j].lower() in HEADER_WORDS:
                j -= 1
                continue
            if is_county_header(lines[j]):
                break
            out.insert(0, lines[j])
        j -= 1
    return out


def clean_name(name: str) -> str:
    # Strip stray page-number prefixes from first record in a county block
    name = re.sub(r"^\d+\s+", "", name).strip()
    return name


def parse_lihtc_properties(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    county: str | None = None

    for i, line in enumerate(lines):
        if not line:
            continue
        if is_county_header(line):
            if line != "HOUSING AUTHORITIES":
                county = normalize_county(line)
            continue
        if line not in ("Family", "Senior"):
            continue

        fwd = nonempty_after(lines, i, 2)
        if len(fwd) < 2:
            continue
        units_s, bed_s = fwd[0], fwd[1]
        if not units_s.isdigit() or not re.match(r"^[\d,\s]+$", bed_s):
            continue

        stop = prev_record_stop(lines, i)
        back = [
            b for b in nonempty_before(lines, i, stop)
            if b.lower() not in HEADER_WORDS and b != "# of"
        ]
        if len(back) < 4:
            continue

        phone, zip_code, city = back[-1], back[-2], back[-3]
        if not re.match(r"^\d{5}$", zip_code) or not re.search(r"\d{3}", phone):
            continue

        pre = back[:-3]
        if not pre:
            name, address = "Unknown", ""
        elif len(pre) == 1:
            name = address = pre[0]
        else:
            address = pre[-1]
            name = " ".join(pre[:-1])

        name = clean_name(name)
        records.append({
            "county": county or "Unknown",
            "name": name,
            "address": address,
            "city": city,
            "zip": zip_code,
            "phone": phone,
            "property_type": line,
            "units": int(units_s),
            "bed_types": bed_s.replace(" ", ""),
            "source": "fitzgerald_pdf_lihtc",
            "data_quality": "complete",
        })

    return records


def is_zip_line(line: str) -> bool:
    return bool(re.match(r"^(\d{5})(,\s*\d{5})*$", line))


def parse_alt_denver_list(lines: list[str]) -> list[dict]:
    """Secondary list: name, address, zip, optional phone(s). No unit/type data."""
    try:
        start = lines.index("DENVER", 3500)
    except ValueError:
        return []

    end = len(lines)
    for marker in ("RESOURCE LINKS", "WESTMINSTER", "WHEAT RIDGE"):
        try:
            end = min(end, lines.index(marker, start))
        except ValueError:
            pass

    chunk = [l for l in lines[start + 1 : end] if l]
    records: list[dict] = []
    i = 0
    while i < len(chunk):
        if is_zip_line(chunk[i]) or chunk[i].startswith("(") or chunk[i].startswith("http"):
            i += 1
            continue
        if i + 2 >= len(chunk):
            break

        name = chunk[i]
        address = chunk[i + 1]
        zip_line = chunk[i + 2]
        if not is_zip_line(zip_line):
            i += 1
            continue

        phone_parts: list[str] = []
        j = i + 3
        while j < len(chunk):
            nxt = chunk[j]
            if is_zip_line(nxt):
                break
            if re.search(r"\d{3}", nxt) and ("(" in nxt or "-" in nxt or "." in nxt):
                phone_parts.append(nxt)
                j += 1
                continue
            break

        records.append({
            "county": "Denver",
            "name": name,
            "address": address,
            "city": "Denver",
            "zip": zip_line.split(",")[0].strip(),
            "phone": " / ".join(phone_parts) if phone_parts else None,
            "property_type": "Unknown",
            "units": None,
            "bed_types": None,
            "source": "fitzgerald_pdf_alt_denver",
            "data_quality": "partial",
        })
        i = j if j > i + 3 else i + 3

    return records


def parse_housing_authorities(lines: list[str]) -> list[dict]:
    try:
        start = lines.index("HOUSING AUTHORITIES")
    except ValueError:
        return []

    names: list[str] = []
    urls: list[str] = []
    for line in lines[start + 1 :]:
        line = line.strip()
        if not line:
            continue
        if line.startswith("www."):
            urls.append("https://" + line)
        elif line.startswith("LINK FOR") or line.startswith("AFFORDABLE") or line.startswith("QUESTIONS"):
            break
        elif "://" not in line and line != "HOUSING AUTHORITIES":
            names.append(line.title().replace(" County", ""))

    return [{"name": n, "website": u, "slug": slugify(n)} for n, u in zip(names, urls)]


def dedupe_properties(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for rec in records:
        key = property_key(rec["name"], rec.get("address", ""), rec.get("zip", ""))
        if key in seen:
            continue
        seen.add(key)
        rec["external_key"] = key
        unique.append(rec)
    return unique


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def seed_properties(conn: sqlite3.Connection, records: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    for rec in records:
        cur.execute(
            """
            INSERT OR IGNORE INTO properties (
                external_key, name, address, city, zip, county, phone,
                property_type, units, bed_types, source, data_quality
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec["external_key"], rec["name"], rec.get("address"), rec.get("city"),
                rec.get("zip"), rec.get("county"), rec.get("phone"),
                rec.get("property_type"), rec.get("units"), rec.get("bed_types"),
                rec.get("source"), rec.get("data_quality"),
            ),
        )
        if cur.rowcount:
            inserted += 1
            prop_id = cur.lastrowid
            cur.execute(
                """
                INSERT OR IGNORE INTO waitlist_profiles (property_id, status, follow_up_interval_days)
                VALUES (?, 'unknown', 90)
                """,
                (prop_id,),
            )
    return inserted


def seed_authorities(conn: sqlite3.Connection, authorities: list[dict]) -> int:
    cur = conn.cursor()
    count = 0
    for auth in authorities:
        cur.execute(
            """
            INSERT OR IGNORE INTO housing_authorities (name, slug, website, jurisdiction)
            VALUES (?, ?, ?, ?)
            """,
            (auth["name"], auth["slug"], auth["website"], auth["name"]),
        )
        if cur.rowcount:
            count += 1
    return count


def link_dha(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE properties
        SET housing_authority_id = (
            SELECT id FROM housing_authorities WHERE slug = 'denver' LIMIT 1
        )
        WHERE county = 'Denver' AND housing_authority_id IS NULL
        """
    )


def seed_client(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO clients (slug, full_name, email, phone, status, notes)
        VALUES (?, ?, ?, ?, 'active', ?)
        """,
        (
            "chad-brizendine",
            "Chad Brizendine",
            "therealchadbrizendine@yahoo.com",
            "+13039003287",
            "Client #1 — primary housing mission.",
        ),
    )
    client_id = conn.execute(
        "SELECT id FROM clients WHERE slug = 'chad-brizendine'"
    ).fetchone()[0]
    conn.execute(
        """
        INSERT OR IGNORE INTO client_requirements (
            client_id, target_counties, property_types, notes
        ) VALUES (?, ?, ?, ?)
        """,
        (
            client_id,
            json.dumps(["Denver", "Adams", "Jefferson", "Arapahoe", "Boulder", "Douglas"]),
            json.dumps(["Family"]),
            "Requirements to refine during first briefing session.",
        ),
    )


def seed_templates(conn: sqlite3.Connection) -> None:
    questions = [
        "Are you accepting applications for low income housing?",
        "How long is the wait list?",
        "How many apartments in the complex have the bedroom size I require?",
        "What is the typical rent amount for the type of apartment I require?",
        "Is there an application fee? How much? Do you provide results and a receipt?",
        "What is the waitlist procedure? Should I call back regularly?",
        "What documents are needed for the application?",
        "What is the best time and place to fill out and return the application?",
        "Are there restrictions on who can reside in the housing (evictions, felonies, pets)?",
        "Is there a minimum/maximum income requirement?",
        "Who should I ask to speak to if I need to get in touch again?",
        "What is their phone number, extension, and email?",
    ]
    body = (
        "Hello,\n\n"
        "I am searching for affordable housing and reaching out to learn about your waitlist.\n\n"
        + "\n".join(f"- {q}" for q in questions)
        + "\n\nThank you for your time.\n\nChad Brizendine\ntherealchadbrizendine@yahoo.com\n(303) 900-3287"
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO outreach_templates (slug, name, channel, subject, body)
        VALUES (?, ?, 'email', ?, ?)
        """,
        (
            "waitlist-intel-inquiry",
            "Waitlist intelligence inquiry",
            "Affordable housing waitlist inquiry",
            body,
        ),
    )


def seed_source_document(conn: sqlite3.Connection) -> None:
    if not PDF_PATH.exists():
        return
    dest = ROOT / "data" / "Affordable Housing LIst.pdf"
    if not dest.exists():
        dest.write_bytes(PDF_PATH.read_bytes())
    client_id = conn.execute(
        "SELECT id FROM clients WHERE slug = 'chad-brizendine'"
    ).fetchone()
    if not client_id:
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO documents (client_id, title, file_path, mime_type, doc_type, notes)
        VALUES (?, ?, ?, 'application/pdf', 'reference', ?)
        """,
        (
            client_id[0],
            "Affordable Housing List (Alexander Fitzgerald)",
            str(dest),
            "Source list from Alexander Fitzgerald / Wellpower, June 2026.",
        ),
    )


def main() -> int:
    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}", file=sys.stderr)
        return 1

    lines = extract_pdf_text(PDF_PATH)
    lihtc = parse_lihtc_properties(lines)
    alt = parse_alt_denver_list(lines)
    authorities = parse_housing_authorities(lines)
    all_props = dedupe_properties(lihtc + alt)

    conn = connect_db()
    try:
        seed_client(conn)
        seed_templates(conn)
        auth_n = seed_authorities(conn, authorities)
        prop_n = seed_properties(conn, all_props)
        link_dha(conn)
        seed_source_document(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"Database: {DB_PATH}")
    print(f"Properties seeded: {prop_n} ({len(all_props)} unique parsed)")
    print(f"  LIHTC complete: {len(lihtc)}")
    print(f"  Alt Denver partial: {len(alt)}")
    print(f"Housing authorities: {auth_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())