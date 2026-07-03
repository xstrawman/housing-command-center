#!/usr/bin/env python3
"""Send approved outreach emails via Himalaya (daily cap enforced)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.db import get_client
from agents.sender import send_approved_batch

def main():
    client = get_client("chad-brizendine")
    if not client:
        print("Client not found")
        return 1
    results = send_approved_batch(client["id"])
    if not results:
        print("No approved emails to send (approve drafts in app first).")
        return 0
    for r in results:
        if r.get("ok"):
            print(f"  SENT #{r['id']} → {r.get('to')}")
        else:
            print(f"  FAIL #{r['id']}: {r.get('error')}")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"\n{ok}/{len(results)} sent")
    return 0 if ok or results else 1

if __name__ == "__main__":
    raise SystemExit(main())