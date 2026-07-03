# Housing Command Center — Complete Session Archive

> **This is the comprehensive README for the July 3, 2026 build session.**  
> For day-to-day usage, see `README.md` in the project root.  
> For strategy whitepaper, see `docs/whitepaper/Housing_Command_Center_Whitepaper.pdf`.

**Date:** July 3, 2026
**Client:** Chad Brizendine (Capitol Hill, Denver 80203)  
**Project root:** `/home/mountaindewurbest/housing-command-center/`  
**Mission:** Personal housing operations system to fight homelessness — scaled later to an agentic case-manager team.

This document records **everything built in today's session**: user requests, agent reasoning, architecture decisions, prompts, code outputs, commands, errors, and the roadmap.

---

## Table of Contents

1. [Session chronology](#1-session-chronology)
2. [User requests and agent thought process](#2-user-requests-and-agent-thought-process)
3. [Architecture decisions](#3-architecture-decisions)
4. [Database design](#4-database-design)
5. [Phase 1 agents](#5-phase-1-agents)
6. [Web application](#6-web-application)
7. [Launcher and automation](#7-launcher-and-automation)
8. [Android APK](#8-android-apk)
9. [Email and outreach workflow](#9-email-and-outreach-workflow)
10. [GPU day kit](#10-gpu-day-kit)
11. [Agent prompts (production)](#11-agent-prompts-production)
12. [File inventory](#12-file-inventory)
13. [Commands reference](#13-commands-reference)
14. [Errors resolved](#14-errors-resolved)
15. [Current database state](#15-current-database-state)
16. [Roadmap (not yet built)](#16-roadmap-not-yet-built)

---

## 1. Session chronology

| # | User request | Outcome |
|---|--------------|---------|
| 1 | Open Yahoo inbox; find Alexander Fitzgerald DHA housing list | Found PDF in Downloads; configured Himalaya CLI for Yahoo |
| 2 | Confirm CLI email client | Himalaya at `~/.config/himalaya/` |
| 3 | Build housing database for future agentic case-manager team | 20-table SQLite schema; seeded 253 properties |
| 4 | Agentic team stack advice | LangGraph/Python agents, SQLite, Ollama/NoLlama, human-in-the-loop |
| 5 | GPU rental day planning (96GB VRAM) | Deferred; slim GPU kit after Phase 1 |
| 6 | Resume incomplete project first | Agreed: agents → web app → GPU kit |
| 7 | Geographic focus refinement | 5mi from 80203 + west corridor (218 focus properties) |
| 8 | "go" — build Phase 1 agents | Strategist, Outreach Drafter, Sender pipeline |
| 9 | Build web app | FastAPI on port 8787, PWA, systemd auto-start |
| 10 | Easier launch (`hcc`, desktop icon, QR) | `scripts/hcc`, connect page, PWA manifest |
| 11 | Android APK / SSH / TUI for Moto G | Kotlin WebView APK + Termux guide + `hcc-tui` |
| 12 | "go" — install APK via USB | `hcc usb`, adb reverse, APK on device ZD222SZ4JC |
| 13 | App is good — begin GPU day kit | Full `gpu-day-kit/` with export, benchmark, Heretic pipeline |
| 14 | Create archive README + whitepaper PDF | This document + 10-page PDF whitepaper |

---

## 2. User requests and agent thought process

### 2.1 Email discovery (Alexander Fitzgerald)

**User prompt:**
> open my yahoo email inbox and locate a document from alexander fitzgerald - its a list of DHA housing buildings

**Agent reasoning:**
- Yahoo Mail requires authentication; browser scraping blocked (Firecrawl API key required).
- Discovered **Himalaya** CLI at `~/.config/himalaya/` — proper path for programmatic email.
- Found local PDF: `~/Downloads/Affordable Housing LIst.pdf` (source: Alexander Fitzgerald / Wellpower, June 2026).

**Outcome:** PDF used as seed source; copied to `data/Affordable Housing LIst.pdf`.

---

### 2.2 Housing database for agentic operations

**User goal:** Waitlist tracking, outreach, daily 15-minute briefings; start with Chad, scale to many clients.

**Agent reasoning:**
- SQLite local-first (no cloud dependency, works offline, phone-over-SSH friendly).
- Separate **inventory** (properties) from **client state** (`client_waitlist_status`).
- Human-in-the-loop for outbound email (`outreach_requires_approval = 1`).
- Cap daily agent output at 5 emails + ~8 tasks to match 15-minute briefing constraint.

**Outcome:** `db/schema.sql` (20 tables), `scripts/seed_from_pdf.py`.

---

### 2.3 Geographic focus evolution

| Stage | Scope |
|-------|-------|
| Initial | 10 miles from 80203 |
| Refined | 5 miles from 80203 |
| Final | **5 miles + west corridor** |

**Final `focus_filter` (in `agent_config`):**

```json
{
  "origin_zip": "80203",
  "radius_miles": 5,
  "west_corridor_zips": [
    "80022", "80030", "80031", "80033", "80204", "80211", "80212",
    "80214", "80215", "80216", "80226", "80227", "80232", "80235"
  ],
  "include_cities": [
    "arvada", "commerce city", "denver", "edgewater", "federal heights",
    "lakewood", "westminster", "wheat ridge"
  ],
  "neighborhoods": [
    "Highlands", "Globeville", "Lakewood", "Westminster", "Wheat Ridge",
    "Edgewater", "Commerce City"
  ],
  "housing_authorities": ["denver", "jefferson", "adams"],
  "description": "5mi from 80203 + west corridor (Highlands, Globeville, Lakewood, Westminster)"
}
```

**Result:** 218 properties in `client_waitlist_status` for client #1.

---

### 2.4 Agent stack

**Approved stack:**

| Layer | Choice |
|-------|--------|
| Database | SQLite (`db/housing.db`) |
| Agents | Python + LangGraph-style pipeline (`agents/graph.py`) |
| LLM (local) | NoLlama Qwen3-8B-int4 on NPU `:11435`; Ollama 30B for hard GPU tasks |
| LLM polish | Optional via `agents/llm.py` (`HCC_LLM_ENABLED`) |
| Email | Himalaya → Yahoo SMTP |
| Phone | Android APK (WebView) + optional Termux SSH + TUI |
| Remote | Cloudflare Tunnel (planned, not built) |

**LLM issue:** NoLlama NPU returned empty/`<think>`-only responses → agents run **rule-based by default** with `HCC_LLM_ENABLED=0`. GPU day kit targets fixing this via Heretic + OpenVINO redeploy.

---

### 2.5 Web app and phone access

**User need:** Open briefing quickly; use phone at library/home.

**Solutions built:**
- `hcc` one-command launcher (systemd + browser)
- PWA manifest for install-to-homescreen
- `/connect` page with QR code
- Native Android APK with USB port forwarding (`adb reverse tcp:8787`)
- Terminal UI (`hcc-tui`) for SSH/Termux

---

### 2.6 GPU day kit

**User prompt:** App is good — begin GPU day kit.

**Agent reasoning:**
- Prep work runnable **without GPU** (export, prefill JSONL).
- GPU rental day: Heretic abliterate → OpenVINO INT4 → NoLlama NPU.
- Benchmark harness uses **same prompts** as production agents.
- Synthetic data (2000 email replies) + LoRA config for future Intel Parser agent.

---

## 3. Architecture decisions

```
┌─────────────────────────────────────────────────────────────────┐
│                     Chad (human in the loop)                     │
│   Approve emails · Make calls · 15 min/day on Today briefing    │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
    ┌────────▼────────┐              ┌───────▼────────┐
    │  Web / APK / TUI │              │  Himalaya send │
    │  FastAPI :8787   │              │  (approved only)│
    └────────┬────────┘              └───────┬────────┘
             │                               │
    ┌────────▼───────────────────────────────▼────────┐
    │              SQLite db/housing.db                │
    │  properties · waitlist_profiles · outreach_queue │
    │  daily_briefings · tasks · agent_runs            │
    └────────┬───────────────────────────────────────┘
             │
    ┌────────▼────────┐     ┌─────────────────────────┐
    │ Daily pipeline  │────▶│ NoLlama / Ollama (LLM)  │
    │ graph.py        │     │ polish + future parser  │
    └─────────────────┘     └─────────────────────────┘
```

**Design principles:**
1. **15-minute daily dose** — never overwhelm; cap emails and tasks.
2. **Call-first for missing emails** — most properties have phone only.
3. **Audit trail** — `agent_runs`, `outreach_log`, `waitlist_observations`.
4. **Client #1 today, many tomorrow** — `clients` table multi-tenant ready.

---

## 4. Database design

**Path:** `db/schema.sql`, `db/housing.db`

**20 tables (groups):**

| Group | Tables |
|-------|--------|
| Clients | `clients`, `client_requirements`, `client_waitlist_status` |
| Inventory | `properties`, `housing_authorities` |
| Waitlist intel | `waitlist_profiles`, `waitlist_observations`, `waitlist_windows` |
| Outreach | `contacts`, `outreach_templates`, `outreach_queue`, `outreach_log` |
| Daily ops | `daily_briefings`, `tasks` |
| System | `documents`, `agent_runs`, `agent_config` |

**Migration v2** (`scripts/migrate_v2.py`): added `properties.email`, `outreach_queue.recipient_email`.

**Seed script:** `scripts/seed_from_pdf.py`
- Parses `Affordable Housing LIst.pdf` via `pdftotext`
- LIHTC property list + alternate Denver list
- 14 housing authorities including DHA (`denverhousing.org`)
- Outreach template `waitlist-intel-inquiry` with 12 intelligence questions

---

## 5. Phase 1 agents

**Directory:** `agents/`

### 5.1 Strategist (`agents/strategist.py`)

- Scores 218 focus properties (partial data, unknown waitlist, follow-up due, opening soon).
- Produces ~8 tasks targeting ~15 minutes.
- Task types: `call`, `email`, `research`.
- Writes `daily_briefings` + `tasks`.
- Optional LLM polish on summary via `polish_text()`.

### 5.2 Outreach Drafter (`agents/outreach.py`)

- Selects up to 5 properties/day (unknown/closed waitlist, not already queued).
- Personalizes `waitlist-intel-inquiry` template.
- Inserts into `outreach_queue` as `draft`.
- Sets `next_follow_up_date` +90 days on `waitlist_profiles`.

### 5.3 Sender (`agents/sender.py`)

- Sends `approved` emails via Himalaya (`himalaya template send -a yahoo`).
- Strips internal property header block from outbound body.
- Respects `daily_email_cap` and requires `recipient_email`.

### 5.4 LLM layer (`agents/llm.py`)

```python
# Ollama-compatible chat API
POST {HCC_LLM_URL}/api/chat
model: Qwen3-8B-int4-cw
prompt prefix: /no_think\n{prompt}
options: num_predict=400, temperature=0.3
```

### 5.5 Pipeline (`agents/graph.py`)

```
run_daily_pipeline()
  → run_strategist()   # briefing + tasks
  → run_outreach()     # draft emails
  → log_agent_run()
```

**Entry:** `python3 scripts/run_daily.py --force`

---

## 6. Web application

**Stack:** FastAPI + Jinja2 + vanilla CSS/JS  
**Port:** 8787 (`HCC_PORT`)  
**Entry:** `app/main.py`

### Pages

| Route | Purpose |
|-------|---------|
| `/today` | Daily briefing + task list |
| `/outreach` | Draft/approve outreach emails |
| `/outreach/{id}` | Edit draft, set recipient email |
| `/properties` | Search 218 focus buildings |
| `/connect` | QR + LAN URL for phone pairing |

### API (JSON)

- `GET /api/health`
- `GET /api/briefing/today`
- `GET /api/tasks`
- `GET /api/outreach`

### PWA

- `app/static/manifest.json`
- `app/static/sw.js`
- `app/static/icon.svg`

### Systemd

- `systemd/hcc-web.service` — auto-start on login
- `scripts/start_web.sh`

---

## 7. Launcher and automation

**`scripts/hcc`** — master launcher:

| Command | Action |
|---------|--------|
| `hcc` | Start server if needed, open browser |
| `hcc qr` | QR pairing page |
| `hcc url` | Print URLs |
| `hcc status` | Service health |
| `hcc daily` | Regenerate briefing |
| `hcc tui` | Terminal menu |
| `hcc usb` | adb reverse + install APK |
| `hcc build-apk` | Rebuild Android APK |
| `hcc send` | Send approved emails |
| `hcc termux` | Phone SSH setup guide |
| `hcc gpu-day` | GPU rental kit |

**Daily timer:** `systemd/hcc-daily.timer` — 7:00 AM → `hcc-daily.service`

---

## 8. Android APK

**Package:** `org.hcc.commandcenter`  
**APK:** `dist/HousingCommand-v1.0.0.apk` (5.6 MB)  
**Device:** Moto G Stylus 5G 2024 (`ZD222SZ4JC`)

**Architecture:** Kotlin WebView → `http://127.0.0.1:8787/today` (USB via `adb reverse`)

**Build:** `android/scripts/build-apk.sh` (local JDK/SDK in `android/.tools/`)

**Fix applied:** `compileSdk` 34 → 35 for Gradle compatibility.

**Settings:** User can set LAN URL for Wi‑Fi mode.

---

## 9. Email and outreach workflow

**Account:** `therealchadbrizendine@yahoo.com` (Himalaya, account `yahoo`)

**Workflow (most properties lack email in DB):**

1. Agent drafts outreach (questions only, phone on file).
2. Chad **calls** property → obtains email.
3. Chad enters `recipient_email` in web UI.
4. Chad approves draft.
5. `hcc send` → Himalaya → Yahoo SMTP.

**Outreach template questions (12):**
1. Accepting applications?
2. Wait list length?
3. Bedroom availability?
4. Typical rent?
5. Application fee + receipt?
6. Waitlist procedure / call-back?
7. Required documents?
8. Best time/place to apply?
9. Residency restrictions (evictions, felonies, pets)?
10. Income min/max?
11. Contact person for follow-up?
12. Phone, extension, email?

---

## 10. GPU day kit

**Path:** `gpu-day-kit/`  
**Prep command:** `hcc gpu-day prep` (already run)

### Pre-generated assets

| File | Count |
|------|-------|
| `exports/outreach_batch.jsonl` | 218 outreach polish prompts |
| `exports/synthetic_batch.jsonl` | 2000 synthetic email-reply prompts |
| `exports/20260703T221422Z/` | DB snapshot + manifest |

### GPU rental pipeline

```
Qwen/Qwen3-8B
    → heretic (abliteration)
    → ~/models/Qwen3-8B-heretic
    → optimum-cli export openvino (INT4 symmetric)
    → ~/models/Qwen3-8B-heretic-int4-cw-ov
    → symlink ~/NoLlama/model
    → NPU inference :11435
```

### Scripts

| Script | Purpose |
|--------|---------|
| `export_bundle.py` | Snapshot DB + JSON exports |
| `prefill_outreach.py` | 218 outreach JSONL |
| `prefill_synthetic.py` | 2000 synthetic prompts |
| `benchmark.py` | Agent prompt benchmarks |
| `batch_generate.py` | GPU batch inference |
| `merge_synthetic.py` | LoRA training JSONL |
| `run_heretic.sh` | Step 1 |
| `export_openvino.sh` | Step 2 |
| `deploy_to_nollama.sh` | Step 3 |

### LoRA config

`gpu-day-kit/lora/housing_case_manager.yaml` — Qwen3-8B, rank 64, 96GB VRAM batch settings.

---

## 11. Agent prompts (production)

### Briefing polish (Strategist)

```
Rewrite this housing briefing summary in 3 short, direct sentences for Chad:
{summary_lines}
```

### Outreach polish (Outreach Drafter)

```
Tighten this outreach email (keep all questions, stay professional):

{personalized_body}
```

### LLM API wrapper

```
/no_think
{prompt}
```

### Benchmark cases

See `gpu-day-kit/prompts/benchmark.json` — 5 cases:
- `briefing_polish`
- `outreach_polish_sample`
- `waitlist_parse_closed`
- `waitlist_parse_open`
- `task_prioritization`

### Synthetic email reply (GPU training)

See `gpu-day-kit/prompts/synthetic_email_reply.txt` — 6 tones cycling across 218 properties.

---

## 12. File inventory

```
housing-command-center/
├── README.md                          # Quick operational guide
├── docs/
│   ├── PROJECT_SESSION_ARCHIVE.md     # This file
│   └── whitepaper/
│       ├── Housing_Command_Center_Whitepaper.md
│       └── Housing_Command_Center_Whitepaper.pdf
├── db/
│   ├── schema.sql
│   └── housing.db
├── data/
│   └── Affordable Housing LIst.pdf
├── agents/
│   ├── config.py, db.py, llm.py
│   ├── strategist.py, outreach.py, sender.py
│   └── graph.py
├── app/
│   ├── main.py, api_routes.py, net.py
│   ├── templates/ (today, outreach, properties, connect)
│   └── static/ (style.css, app.js, manifest.json, sw.js)
├── android/                           # Kotlin WebView APK project
├── dist/HousingCommand-v1.0.0.apk
├── gpu-day-kit/                       # GPU rental kit
├── scripts/
│   ├── hcc, hcc-tui, run_daily.py
│   ├── seed_from_pdf.py, send_approved.py
│   ├── phone-usb.sh, termux-on-phone.sh
│   └── generate_whitepaper_pdf.py
└── systemd/
    ├── hcc-web.service
    ├── hcc-daily.service
    └── hcc-daily.timer
```

---

## 13. Commands reference

```bash
# Daily operations
hcc                          # Open briefing
hcc daily                    # Regenerate agents
hcc send                     # Send approved emails
python3 scripts/show_briefing.py

# Phone
hcc usb                      # USB: adb reverse + APK
hcc qr                       # Wi-Fi QR pairing
hcc tui                      # Terminal UI

# Database
python3 scripts/seed_from_pdf.py
python3 scripts/db_summary.py

# Documentation
python3 scripts/generate_whitepaper_pdf.py   # rebuild 10-page PDF

# GPU day
hcc gpu-day prep
hcc gpu-day benchmark --compare
hcc gpu-day heretic
hcc gpu-day openvino
hcc gpu-day deploy

# Services
systemctl --user status hcc-web.service
systemctl --user enable --now hcc-daily.timer
```

---

## 14. Errors resolved

| Issue | Fix |
|-------|-----|
| Firecrawl/Yahoo browser login blocked | Used Himalaya CLI + local PDF |
| NoLlama empty LLM responses | Rule-based agents; `HCC_LLM_ENABLED=0` default |
| FastAPI `TemplateResponse` API change | `request=`, `name=`, `context=` kwargs |
| APK build `compileSdk 34` failure | Upgraded to SDK 35 |
| `hcc phone` command conflict | Split into `hcc qr` and `hcc usb` |
| Properties lack emails | `recipient_email` field + call-first workflow |
| PDF-parsed property name quality | `data_quality: partial` flag; research tasks |

---

## 15. Current database state

*(Snapshot: July 3, 2026)*

| Metric | Count |
|--------|-------|
| Total properties | 253 |
| Focus properties (client #1) | 218 |
| Housing authorities | 14 |
| Outreach queue | 5 drafts |
| Daily briefings | 1 |
| Tasks (today) | 8 |

**Client #1:** Chad Brizendine  
**Email:** therealchadbrizendine@yahoo.com  
**Phone:** (303) 900-3287

---

## 16. Roadmap (not yet built)

| Phase | Feature |
|-------|---------|
| 2 | **Intel Parser agent** — parse email replies → `waitlist_profiles` JSON |
| 2 | Fix NoLlama NPU LLM inference (GPU day Heretic deploy) |
| 3 | **Cloudflare Tunnel** — access outside home Wi‑Fi |
| 3 | Multi-client onboarding |
| 4 | Embeddings / semantic property search |
| 4 | LoRA fine-tune on synthetic housing data |
| 5 | Scale agentic case-manager team |

---

## Appendix A: Environment and paths

| Resource | Path |
|----------|------|
| Project | `~/housing-command-center/` |
| Database | `~/housing-command-center/db/housing.db` |
| Himalaya config | `~/.config/himalaya/` |
| NoLlama | `~/NoLlama/` (port 11435) |
| NPU model | `~/models/Qwen3-8B-int4-cw-ov` |
| Agentic venv | `~/agentic-ai/venv/` |
| Session transcript | `~/.grok/sessions/.../updates.jsonl` |

---

## Appendix B: Key configuration (`agents/config.py`)

```python
DB_PATH = ROOT / "db" / "housing.db"
CLIENT_SLUG = "chad-brizendine"
OLLAMA_BASE_URL = "http://127.0.0.1:11435"
OLLAMA_MODEL = "Qwen3-8B-int4-cw"
LLM_ENABLED = os.environ.get("HCC_LLM_ENABLED", "1") == "1"
DAILY_EMAIL_CAP = 5
BRIEFING_MINUTES = 15
OUTREACH_BATCH_SIZE = 5
```

---

*End of session archive. For operational quick-start, see `README.md`. For GPU rental, see `gpu-day-kit/README.md`. For strategy whitepaper, see `docs/whitepaper/Housing_Command_Center_Whitepaper.pdf`.*