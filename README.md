# Housing Command Center

Local database and operations hub for defeating homelessness — one daily 15-minute briefing at a time.

**GitHub:** https://github.com/xstrawman/housing-command-center  
**Full session archive:** [`COMPLETE_README.md`](COMPLETE_README.md) — everything built July 3, 2026 (user prompts, agent reasoning, architecture, code inventory).  
**Whitepaper (PDF):** on Trom Files only → `HousingCommandCenter/Housing_Command_Center_Whitepaper.pdf` (markdown source in `docs/whitepaper/`)

## What's here now

- **SQLite database** at `db/housing.db`
- **253 properties** seeded from Alexander Fitzgerald's Affordable Housing List
- **14 housing authorities** including DHA (`denverhousing.org`)
- **Client #1:** Chad Brizendine
- **Outreach template** with waitlist intelligence questions

## Android phone (APK — installed on your Moto G)

**Housing Command** app — native APK wrapping your briefing UI.

| Mode | Setup |
|------|--------|
| **USB (plugged in)** | `hcc usb` — forwards port, app uses `http://127.0.0.1:8787` |
| **Wi‑Fi** | App menu → Settings → `http://YOUR_PC_IP:8787/today` |

```bash
hcc build-apk   # rebuild APK
hcc usb         # adb reverse + install + launch
```

APK file: `dist/HousingCommand-v1.0.0.apk`

Enable **USB debugging** on phone (Developer options). Accept install prompt when prompted.

## SSH + Terminal UI (Termux)

```bash
hcc termux      # full setup guide
hcc tui         # terminal menu on PC (works over SSH too)
```

On PC enable SSH: `sudo systemctl enable --now sshd`  
From Termux: `ssh user@PC_IP` then `HCC_URL=http://127.0.0.1:8787 hcc-tui`

## Web app (browser)

| How | What |
|-----|------|
| **`hcc`** | Terminal — starts server if needed, opens browser |
| **Desktop icon** | "Housing Command Center" in app menu |
| **QR** | `hcc qr` — pairing page for Wi‑Fi |

```bash
hcc          # open today's briefing
hcc phone    # QR for your phone (same Wi‑Fi)
hcc status   # is the server running?
hcc daily    # regenerate briefing
```

Server auto-starts on login. Manual: `systemctl --user start hcc-web.service`

Install to phone home screen: Chrome → **Install app** (PWA).

Pages: **Today** (briefing + tasks), **Outreach** (approve emails), **Properties** (search 218 focus buildings).

## Commands

```bash
# Run today's agent pipeline (briefing + outreach drafts)
python3 scripts/run_daily.py --force

# View today's briefing (terminal)
python3 scripts/show_briefing.py

# Re-seed from PDF (safe to re-run)
python3 scripts/seed_from_pdf.py

# Database summary
python3 scripts/db_summary.py
```

## GPU day kit

Prep now (no GPU needed):

```bash
hcc gpu-day prep
```

On GPU rental day: Heretic abliteration → OpenVINO INT4 → NoLlama NPU deploy, benchmarks, synthetic data, LoRA config. See `gpu-day-kit/README.md`.

## Daily automation (optional)

```bash
mkdir -p ~/.config/systemd/user
cp systemd/hcc-daily.service systemd/hcc-daily.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hcc-daily.timer
```

## Next build phases

1. **Intel Parser agent** — parse email replies, update waitlist windows
2. **Himalaya send agent** — send approved outreach emails
3. **Cloudflare Tunnel** — access from outside your home Wi‑Fi (library, etc.)