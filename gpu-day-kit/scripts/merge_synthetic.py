#!/usr/bin/env python3
"""Convert generated synthetic JSONL into LoRA training JSONL (Alpaca format)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = KIT / "exports" / "housing_case_manager_train.jsonl"

INSTRUCTION_PARSE = (
    "Extract waitlist intelligence from this property email reply. "
    "Return ONLY valid JSON with keys: property_name, status, wait_time_estimate, "
    "typical_open_month, application_method, application_fee, documents_required, "
    "rental_criteria, min_income, max_income, contact_name, contact_phone, "
    "contact_email, confidence_score, raw_notes."
)

INSTRUCTION_POLISH = (
    "Tighten this outreach email for a housing applicant. "
    "Keep all waitlist questions. Stay professional. Output only the email body."
)


def split_reply_output(text: str) -> tuple[str, dict | None]:
    if "---JSON---" in text:
        body, _, json_part = text.partition("---JSON---")
        body = body.strip()
        json_part = json_part.strip()
        if json_part.startswith("```"):
            json_part = re.sub(r"^```(?:json)?\s*", "", json_part)
            json_part = re.sub(r"\s*```$", "", json_part)
        try:
            return body, json.loads(json_part)
        except json.JSONDecodeError:
            return body, None
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return text[: match.start()].strip(), json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return text, None


def to_alpaca(instruction: str, inp: str, output: str) -> dict:
    return {"instruction": instruction, "input": inp, "output": output}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated", type=Path, help="*_generated.jsonl from batch_generate.py")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-outreach", type=Path, default=None)
    args = parser.parse_args()

    if not args.generated.exists():
        print(f"File not found: {args.generated}", file=sys.stderr)
        return 1

    records: list[dict] = []
    skipped = 0

    with args.generated.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            output = row.get("output", "")
            task = row.get("task", "")

            if task == "synthetic_email_reply":
                reply_body, extracted = split_reply_output(output)
                if not reply_body or not extracted:
                    skipped += 1
                    continue
                records.append(
                    to_alpaca(
                        INSTRUCTION_PARSE,
                        f"Property: {row.get('property_name', '')}\nReply:\n{reply_body}",
                        json.dumps(extracted, ensure_ascii=False),
                    )
                )
            elif task in ("outreach_polish", "outreach_draft"):
                if len(output) < 80:
                    skipped += 1
                    continue
                records.append(
                    to_alpaca(
                        INSTRUCTION_POLISH,
                        row.get("body_draft", row.get("prompt", ""))[:2500],
                        output,
                    )
                )
            else:
                skipped += 1

    if args.include_outreach and args.include_outreach.exists():
        with args.include_outreach.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                output = row.get("output", "")
                if len(output) < 80:
                    skipped += 1
                    continue
                records.append(
                    to_alpaca(
                        INSTRUCTION_POLISH,
                        row.get("body_draft", "")[:2500],
                        output,
                    )
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out_fh:
        for rec in records:
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Training examples: {len(records)} (skipped {skipped}) → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())