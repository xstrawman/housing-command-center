-- Housing Command Center — SQLite schema
-- Personal housing operations DB; client #1 today, many clients tomorrow.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─── Clients ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'paused', 'housed', 'archived')),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS client_requirements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    min_bedrooms        INTEGER,
    max_bedrooms        INTEGER,
    max_rent            REAL,
    monthly_income      REAL,
    target_counties     TEXT,          -- JSON array
    target_cities       TEXT,          -- JSON array
    property_types      TEXT,          -- JSON: ["Family","Senior"]
    needs_section8      INTEGER NOT NULL DEFAULT 0,
    has_pets            INTEGER NOT NULL DEFAULT 0,
    pet_notes           TEXT,
    eviction_history    INTEGER NOT NULL DEFAULT 0,
    felony_restrictions TEXT,
    accessibility_needs TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─── Housing inventory ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS housing_authorities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    website         TEXT,
    phone           TEXT,
    email           TEXT,
    jurisdiction    TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS properties (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_key    TEXT UNIQUE,       -- stable hash for dedup across imports
    name            TEXT NOT NULL,
    address         TEXT,
    city            TEXT,
    zip             TEXT,
    county          TEXT,
    phone           TEXT,
    property_type   TEXT CHECK (property_type IN ('Family', 'Senior', 'Unknown')),
    units           INTEGER,
    bed_types       TEXT,              -- e.g. "1,2,3"
    housing_authority_id INTEGER REFERENCES housing_authorities(id),
    source          TEXT NOT NULL DEFAULT 'manual',
    data_quality    TEXT NOT NULL DEFAULT 'complete'
                    CHECK (data_quality IN ('complete', 'partial', 'needs_review')),
    accepts_section8 INTEGER,
    website         TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_properties_county ON properties(county);
CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_zip ON properties(zip);
CREATE INDEX IF NOT EXISTS idx_properties_name ON properties(name);

-- ─── Waitlist intelligence ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS waitlist_profiles (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id             INTEGER NOT NULL UNIQUE REFERENCES properties(id) ON DELETE CASCADE,
    status                  TEXT NOT NULL DEFAULT 'unknown'
                            CHECK (status IN (
                                'unknown', 'closed', 'open', 'opening_soon',
                                'by_appointment', 'lottery', 'not_applicable'
                            )),
    typical_open_month      TEXT,          -- e.g. "March"
    typical_open_duration_days INTEGER,
    last_open_date          TEXT,
    last_close_date         TEXT,
    estimated_next_open     TEXT,
    confidence_score        REAL NOT NULL DEFAULT 0.0,
    follow_up_interval_days INTEGER NOT NULL DEFAULT 90,
    next_follow_up_date     TEXT,
    application_method      TEXT,          -- in_person, online, mail, phone
    application_fee         REAL,
    documents_required      TEXT,
    rental_criteria         TEXT,
    min_income              REAL,
    max_income              REAL,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS waitlist_observations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    observed_at     TEXT NOT NULL DEFAULT (datetime('now')),
    source          TEXT NOT NULL DEFAULT 'manual'
                    CHECK (source IN ('call', 'email', 'website', 'agent', 'manual', 'import')),
    status          TEXT,
    wait_time_estimate TEXT,
    raw_notes       TEXT NOT NULL,
    contact_name    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS waitlist_windows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    opened_on       TEXT,
    closed_on       TEXT,
    is_predicted    INTEGER NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    source          TEXT NOT NULL DEFAULT 'observation',
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS client_waitlist_status (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    property_id     INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'researching'
                    CHECK (status IN (
                        'researching', 'queued', 'applied', 'on_waitlist',
                        'called_back', 'denied', 'offered', 'accepted', 'withdrawn'
                    )),
    applied_on      TEXT,
    position        TEXT,
    priority        INTEGER NOT NULL DEFAULT 50,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (client_id, property_id)
);

-- ─── Outreach engine ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    housing_authority_id INTEGER REFERENCES housing_authorities(id) ON DELETE SET NULL,
    name            TEXT,
    role            TEXT,
    email           TEXT,
    phone           TEXT,
    extension       TEXT,
    best_time       TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outreach_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'email'
                    CHECK (channel IN ('email', 'phone', 'sms')),
    subject         TEXT,
    body            TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outreach_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    contact_id      INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
    template_id     INTEGER REFERENCES outreach_templates(id) ON DELETE SET NULL,
    channel         TEXT NOT NULL DEFAULT 'email'
                    CHECK (channel IN ('email', 'phone', 'sms')),
    subject         TEXT,
    body            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'approved', 'scheduled', 'sent', 'failed', 'cancelled')),
    priority        INTEGER NOT NULL DEFAULT 50,
    scheduled_for   TEXT,
    sent_at         TEXT,
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id        INTEGER REFERENCES outreach_queue(id) ON DELETE SET NULL,
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    channel         TEXT NOT NULL,
    direction       TEXT NOT NULL DEFAULT 'outbound'
                    CHECK (direction IN ('outbound', 'inbound')),
    subject         TEXT,
    body            TEXT,
    sent_at         TEXT NOT NULL DEFAULT (datetime('now')),
    response_body   TEXT,
    response_at     TEXT,
    parsed_intel    TEXT,              -- JSON extracted by agents
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─── Daily operations (15-minute doses) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS daily_briefings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    briefing_date   TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    urgent_flags    TEXT,              -- JSON array
    estimated_minutes INTEGER NOT NULL DEFAULT 15,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped')),
    completed_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (client_id, briefing_date)
);

CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    briefing_id     INTEGER REFERENCES daily_briefings(id) ON DELETE SET NULL,
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    task_type       TEXT NOT NULL DEFAULT 'general'
                    CHECK (task_type IN (
                        'call', 'email', 'print', 'apply', 'follow_up',
                        'research', 'review', 'general'
                    )),
    priority        INTEGER NOT NULL DEFAULT 50,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'in_progress', 'done', 'snoozed', 'cancelled')),
    due_date        TEXT,
    estimated_minutes INTEGER,
    completed_at    TEXT,
    completion_notes TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_client_status ON tasks(client_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- ─── Documents & agents ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    property_id     INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    file_path       TEXT,
    mime_type       TEXT,
    doc_type        TEXT NOT NULL DEFAULT 'other'
                    CHECK (doc_type IN (
                        'application', 'letter', 'id', 'income_proof',
                        'reference', 'briefing', 'other'
                    )),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name      TEXT NOT NULL,
    run_type        TEXT NOT NULL DEFAULT 'scheduled',
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'success', 'partial', 'failed')),
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    summary         TEXT,
    error_message   TEXT,
    metadata        TEXT               -- JSON
);

CREATE TABLE IF NOT EXISTS agent_config (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    description     TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Default agent configuration
INSERT OR IGNORE INTO agent_config (key, value, description) VALUES
    ('daily_email_cap', '5', 'Max outreach emails agents send per day'),
    ('briefing_hour_local', '7', 'Hour (24h) to generate morning briefing'),
    ('follow_up_default_days', '90', 'Default days between property follow-ups'),
    ('waitlist_alert_lead_days', '14', 'Days before predicted open to flag in briefing'),
    ('outreach_requires_approval', '1', '1 = Chad approves emails before send');