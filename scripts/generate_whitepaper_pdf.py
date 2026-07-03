#!/usr/bin/env python3
"""Generate Housing Command Center whitepaper PDF from markdown source."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "whitepaper" / "Housing_Command_Center_Whitepaper.md"
OUTPUT = ROOT / "docs" / "whitepaper" / "Housing_Command_Center_Whitepaper.pdf"


class WhitepaperPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, sanitize("Housing Command Center - Whitepaper"), align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def sanitize(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2192": "->",
        "\u2264": "<=",
        "\u00b7": "-",
        "\u2500": "-",
        "\u2502": "|",
        "\u251c": "+",
        "\u2514": "+",
        "\u2524": "+",
        "\u2534": "+",
        "\u250c": "+",
        "\u2510": "+",
        "\u2518": "+",
        "\u2508": "-",
        "\u25bc": "v",
        "\u25b2": "^",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def content_width(pdf: WhitepaperPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def write_para(pdf: WhitepaperPDF, text: str, *, size: int = 10, style: str = "", line_h: float = 5.5) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(content_width(pdf), line_h, sanitize(text))


def write_heading(pdf: WhitepaperPDF, text: str, *, size: int, style: str = "B", line_h: float = 8, color: tuple[int, int, int] | None = None) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", style, size)
    if color:
        pdf.set_text_color(*color)
    pdf.multi_cell(content_width(pdf), line_h, sanitize(text))
    pdf.set_text_color(0, 0, 0)


def render_markdown(pdf: WhitepaperPDF, md_text: str) -> None:
    lines = md_text.splitlines()
    in_code = False
    in_table = False
    table_rows: list[list[str]] = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        col_count = max(len(r) for r in table_rows)
        widths = [pdf.w - pdf.l_margin - pdf.r_margin]
        if col_count == 2:
            widths = [55, pdf.w - pdf.l_margin - pdf.r_margin - 55]
        elif col_count >= 3:
            w = (pdf.w - pdf.l_margin - pdf.r_margin) / col_count
            widths = [w] * col_count
        pdf.set_font("Helvetica", "", 9)
        for i, row in enumerate(table_rows):
            if i == 0:
                pdf.set_font("Helvetica", "B", 9)
            elif i == 1 and all(set(c.strip()) <= set("-:") for c in row):
                continue
            else:
                pdf.set_font("Helvetica", "", 9)
            row = row + [""] * (col_count - len(row))
            for j, cell in enumerate(row[:col_count]):
                pdf.cell(widths[j], 7, sanitize(cell.strip()[:80]), border=1)
            pdf.ln()
        pdf.ln(3)
        table_rows = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            in_code = not in_code
            if not in_code:
                pdf.ln(2)
            else:
                pdf.set_font("Courier", "", 8)
                pdf.set_fill_color(245, 245, 245)
            continue

        if in_code:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Courier", "", 7)
            pdf.set_fill_color(245, 245, 245)
            chunk = sanitize(line)
            if len(chunk) > 110:
                chunk = chunk[:110] + "..."
            pdf.multi_cell(content_width(pdf), 4, chunk, fill=True)
            continue

        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            pdf.ln(6)
            write_heading(pdf, line[2:].strip(), size=20, line_h=10, color=(20, 60, 100))
            continue

        if line.startswith("## "):
            pdf.ln(5)
            write_heading(pdf, line[3:].strip(), size=14, line_h=8, color=(30, 80, 120))
            continue

        if line.startswith("### "):
            pdf.ln(4)
            write_heading(pdf, line[4:].strip(), size=11, line_h=7)
            continue

        if line.startswith("---"):
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            continue

        if line.startswith("- [ ]") or line.startswith("- [x]") or line.startswith("- [X]"):
            mark = "[x]" if "[x]" in line.lower() else "[ ]"
            write_para(pdf, f"  {mark} {line[5:].strip()}")
            continue

        if line.startswith("- "):
            write_para(pdf, f"  - {line[2:].strip()}")
            continue

        if re.match(r"^\d+\.\s", line):
            write_para(pdf, f"  {line.strip()}")
            continue

        if line.startswith("**") and line.endswith("**"):
            write_para(pdf, line.strip("*"), style="B", line_h=6)
            continue

        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        write_para(pdf, clean)

    if in_table:
        flush_table()


def main() -> int:
    if not SOURCE.exists():
        print(f"Source not found: {SOURCE}", file=sys.stderr)
        return 1

    md_text = SOURCE.read_text(encoding="utf-8")
    pdf = WhitepaperPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Cover block
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(20, 60, 100)
    pdf.ln(25)
    pdf.multi_cell(0, 12, "Housing Command Center", align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 8, "A Personal Operations System for\nAffordable Housing Navigation", align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(0, 6, sanitize("Whitepaper - July 3, 2026"), align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "Prepared for: Chad Brizendine\nCapitol Hill, Denver, Colorado (80203)", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.add_page()

    render_markdown(pdf, md_text)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"PDF written: {OUTPUT}")
    print(f"Pages: {pdf.page_no()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())