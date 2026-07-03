# Housing Command Center

## A Personal Operations System for Affordable Housing Navigation

**Whitepaper — July 3, 2026**

**Prepared for:** Chad Brizendine  
**Location:** Capitol Hill, Denver, Colorado (80203)

---

## Executive Summary

Housing Command Center (HCC) is a locally hosted operations platform designed to help individuals navigate Denver's fragmented affordable housing landscape through disciplined daily action. Rather than treating housing search as an overwhelming full-time job, HCC compresses the work into a **15-minute daily briefing** backed by a structured database, semi-autonomous AI agents, and human-in-the-loop approval for all outbound communication.

The system was born from a practical need: a comprehensive list of DHA-affiliated and LIHTC properties (provided by Alexander Fitzgerald) had to be transformed from a static PDF into living intelligence — waitlist status, outreach history, follow-up schedules, and actionable tasks.

HCC is built to scale. Client #1 is a personal housing mission today; tomorrow it becomes a template for an **agentic case-manager team** serving many clients fighting homelessness.

---

## 1. The Problem

### 1.1 Information fragmentation

Affordable housing in the Denver metro area is distributed across:

- Multiple housing authorities (DHA, Jefferson County, Adams County, and others)
- Hundreds of LIHTC properties with independent leasing offices
- Inconsistent waitlist policies (open, closed, lottery, by-appointment)
- Phone-only contact for many properties — no published email

A single PDF list of 250+ properties is necessary but insufficient. Without systematic tracking, applicants lose context between calls, repeat questions, miss opening windows, and burn out.

### 1.2 The capacity constraint

Housing search is emotionally and cognitively expensive. Full-time outreach is not sustainable for someone already in housing instability. The design constraint is explicit: **no more than 15 minutes of structured work per day**, with agents doing preparation overnight.

### 1.3 The trust constraint

Automated outreach to housing authorities must be accurate, professional, and controlled. Properties must not receive spam. The applicant must approve every email before send. Calls remain human — agents prepare scripts and track outcomes.

---

## 2. Vision and Goals

### 2.1 Primary aim

**Secure stable affordable housing for Chad Brizendine** by maintaining persistent intelligence on 218 focus properties within 5 miles of 80203 and the west corridor (Highlands, Globeville, Lakewood, Westminster, Commerce City, Wheat Ridge).

### 2.2 Operational goals

| Goal | Metric |
|------|--------|
| Daily engagement | ≤15 minutes |
| Outreach volume | ≤5 emails/day (agent-drafted, human-approved) |
| Coverage | 218 focus properties tracked |
| Follow-up discipline | 90-day default re-contact cycle |
| Waitlist intelligence | Status known or actively researched for every focus property |

### 2.3 Strategic goals

1. **Build institutional memory** — every call, email, and observation persisted in SQLite.
2. **Deploy agentic labor** — agents draft, prioritize, and remind; humans decide and connect.
3. **Run locally** — no cloud dependency; works on a CachyOS laptop with Intel NPU.
4. **Access anywhere** — web app, Android APK, terminal UI over SSH.
5. **Improve models** — GPU day kit for fine-tuned housing case-manager LLM on rented compute.

---

## 3. System Architecture

### 3.1 Layered design

```
┌──────────────────────────────────────────────────────────────┐
│                    Human Operator (Chad)                      │
│         15 min/day · approve emails · make calls              │
└─────────────────────────┬────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌──────────┐    ┌─────────────┐   ┌───────────┐
   │ Web App  │    │ Android APK │   │ TUI/SSH   │
   │ :8787    │    │  WebView    │   │ hcc-tui   │
   └────┬─────┘    └──────┬──────┘   └─────┬─────┘
        └─────────────────┼────────────────┘
                          ▼
              ┌───────────────────────┐
              │   SQLite Database     │
              │   20 tables · WAL     │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   Agent Pipeline      │
              │ Strategist → Outreach │
              │        → Sender       │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   Local LLM (optional)│
              │ NoLlama NPU :11435    │
              └───────────────────────┘
```

### 3.2 Technology choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Database | SQLite | Local, portable, auditable, no ops overhead |
| Backend | FastAPI | Fast iteration, JSON API for TUI/phone |
| Agents | Python pipeline | Simple, debuggable; LangGraph-ready |
| LLM | Qwen3-8B via NoLlama | Fits Intel NPU; Ollama API compatible |
| Email | Himalaya CLI | Scriptable Yahoo SMTP with human credentials |
| Mobile | WebView APK | Reuse web UI; USB port forwarding |

---

## 4. Data Model

### 4.1 Core entities

- **Properties** — 253 seeded from PDF; 218 in active focus for client #1
- **Waitlist profiles** — per-property status, follow-up dates, confidence scores
- **Client waitlist status** — client-specific priority and application state
- **Outreach queue** — draft → approved → sent lifecycle
- **Daily briefings + tasks** — the 15-minute daily plan

### 4.2 Geographic strategy

Focus filter combines:

- **5-mile radius** from origin ZIP 80203
- **West corridor ZIPs** — 80022, 80030, 80031, 80033, 80204, 80211, 80212, 80214, 80215, 80216, 80226, 80227, 80232, 80235
- **Target cities** — Denver, Lakewood, Westminster, Wheat Ridge, Arvada, Commerce City, Edgewater, Federal Heights
- **Housing authorities** — Denver, Jefferson, Adams

This reflects a deliberate strategy: stay close to current location while covering the west corridor where affordable inventory clusters.

---

## 5. Agentic Strategy

### 5.1 Phase 1 agents (deployed)

**Strategist** — Each morning, scores 218 properties and produces ~8 tasks:
- Top 3: call properties with phone numbers (waitlist unknown)
- Next 3: review agent-drafted outreach emails
- Research: fill gaps on partial data records
- Standing: check DHA website for announcements

**Outreach Drafter** — Selects 5 properties/day, personalizes the 12-question waitlist intelligence template, queues drafts for approval.

**Sender** — Sends approved emails via Himalaya after human sets `recipient_email` (call-first workflow).

### 5.2 Human-in-the-loop gates

| Gate | Setting |
|------|---------|
| Email approval required | `outreach_requires_approval = 1` |
| Daily email cap | 5 |
| LLM polish | Optional (`HCC_LLM_ENABLED`) |

### 5.3 Phase 2 agents (planned)

**Intel Parser** — Ingest property email replies; extract structured JSON (status, wait time, fees, documents, contacts) into `waitlist_profiles`.

**GPU-trained case-manager LoRA** — Fine-tuned on 2000+ synthetic email replies for accurate JSON extraction and outreach polish.

---

## 6. Daily Operations Workflow

### Morning (automated, 7:00 AM)

1. `hcc-daily.timer` triggers `run_daily.py`
2. Strategist writes briefing + tasks
3. Outreach Drafter queues 5 email drafts

### Chad's 15 minutes

1. Open `hcc` or phone APK → **Today** page
2. Complete 2–3 call tasks (ask waitlist questions)
3. Enter emails obtained by phone into **Outreach** page
4. Approve/edit drafts
5. `hcc send` for approved items

### Weekly rhythm

- 5 emails × 7 days = 35 properties/week contacted
- 218 properties ÷ 35 ≈ **6 weeks** for first full outreach pass
- 90-day follow-up cycle ensures re-contact without nagging

---

## 7. Access Strategy

### 7.1 Desktop

- `hcc` command → browser → `http://127.0.0.1:8787/today`
- systemd auto-start on login
- Desktop icon: "Housing Command Center"

### 7.2 Android (Moto G Stylus 5G)

- **USB mode:** `hcc usb` — adb reverse, APK uses localhost
- **Wi-Fi mode:** Settings → PC LAN IP
- **QR pairing:** `hcc qr` → `/connect` page

### 7.3 Remote (planned)

- Cloudflare Tunnel for library/outside-WiFi access
- Termux SSH + `hcc-tui` as fallback

---

## 8. AI Model Strategy

### 8.1 Current state

- **NoLlama** serves Qwen3-8B-int4-cw on Intel NPU (port 11435)
- NPU inference returns empty responses for polish tasks → agents run rule-based
- `HCC_LLM_ENABLED=0` by default until model pipeline fixed

### 8.2 GPU day plan

| Step | Action |
|------|--------|
| 1 | Heretic abliteration of Qwen3-8B |
| 2 | OpenVINO INT4 export (symmetric, ratio 1.0) |
| 3 | Deploy to NoLlama NPU |
| 4 | Benchmark agent prompts (before/after) |
| 5 | Generate 2000 synthetic email replies on rented GPU |
| 6 | LoRA fine-tune housing case-manager adapter |

### 8.3 96GB VRAM utilization

Beyond model export:
- Batch outreach polish for all 218 properties
- Synthetic training data at scale
- Optional Qwen3-30B for hard reasoning benchmarks
- Property description embeddings for semantic search

---

## 9. Outreach Intelligence Template

Every outreach email asks twelve standardized questions designed to extract waitlist intelligence in one reply:

1. Application acceptance status
2. Wait list duration
3. Bedroom availability
4. Rent range for required unit type
5. Application fee and receipt policy
6. Waitlist procedure and call-back expectations
7. Required documents
8. Best time and place to apply
9. Residency restrictions
10. Income requirements
11. Contact person for follow-up
12. Phone, extension, and email

This template mirrors what a professional housing case manager would ask — consistent, thorough, respectful.

---

## 10. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Property data stale/incomplete | `data_quality` flags; research tasks in briefing |
| Email spam perception | 5/day cap; human approval; 90-day follow-up interval |
| Model hallucination on waitlist facts | Parser outputs JSON with confidence scores; human verifies |
| NoLlama NPU failures | Rule-based fallback; GPU day redeploy |
| Phone-only contacts | Call tasks prioritized; email field added post-call |
| Burnout | Hard 15-minute cap; agents do prep work |

---

## 11. Success Criteria

### Near-term (30 days)

- [ ] First full outreach pass initiated (35+ properties contacted)
- [ ] 10+ waitlist statuses updated from calls/emails
- [ ] Daily briefing used ≥5 days/week
- [ ] NoLlama LLM polish working after GPU deploy

### Medium-term (90 days)

- [ ] Intel Parser agent processing replies automatically
- [ ] 50%+ focus properties have known waitlist status
- [ ] At least one waitlist opening caught via follow-up cycle

### Long-term

- [ ] Chad housed in affordable unit matching requirements
- [ ] System replicated for additional clients
- [ ] Agentic case-manager team operational

---

## 12. Conclusion

Housing Command Center reframes affordable housing search from chaotic urgency into **disciplined operations**. By combining a structured database, geographic focus, daily briefings, and carefully gated AI agents, the system respects both the applicant's time and the property managers' inboxes.

The work completed on July 3, 2026 — from PDF seed to agents, web app, Android APK, email integration, and GPU preparation kit — establishes a complete operational foundation. The next phases add reply intelligence, model quality, and remote access. The goal is not software for its own sake: it is **a home**.

---

**Housing Command Center**  
`/home/mountaindewurbest/housing-command-center/`  
Chad Brizendine · Denver, CO · July 2026