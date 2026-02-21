# Architecture Document: RTO Intel Pipeline

## 1. Technical Summary

RTO Intel is a Python-based data pipeline that collects RTO intelligence from training.gov.au, detects changes, enriches them with AI analysis via the Anthropic API, and delivers results through Make.com webhooks. It runs as a scheduled batch job with SQLite for local storage.

## 2. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Jimmy's working language; rich ecosystem for HTTP, data, scheduling |
| **HTTP Client** | `httpx` | Async support, built-in retry, cleaner API than requests |
| **Database** | SQLite via `sqlite3` (stdlib) | Zero config, portable, single-file; perfect for single-user pipeline |
| **AI** | Anthropic Python SDK (`anthropic`) | Direct Claude API access, typed responses |
| **Scheduling** | Make.com HTTP webhook → triggers script OR local cron | Make.com for initial simplicity; cron for self-hosted later |
| **Email** | Make.com Gmail module | No SMTP config needed; Jimmy already uses Make.com |
| **Structured Output** | Make.com Google Sheets module or `gspread` | Outreach queue lives in Sheets |
| **Web Scraping** | `httpx` + `beautifulsoup4` | ASQA news monitoring |
| **Config** | `python-dotenv` + `.env` | API keys, webhook URLs, file paths |
| **Data Diffing** | `deepdiff` | Structural comparison of JSON API responses |
| **Deployment** | Railway (free tier) or local cron | Railway for always-on; local for zero-cost |

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MAKE.COM                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐       │
│  │ Schedule  │───▶│ Webhook  │    │ Gmail Module     │       │
│  │ (7am AEST)│    │ Trigger  │    │ (send digest)    │       │
│  └──────────┘    └────┬─────┘    └────────▲─────────┘       │
│                       │                    │                  │
│                       │              ┌─────┴──────────┐      │
│                       │              │ Sheets Module   │      │
│                       │              │ (outreach queue)│      │
│                       │              └────────▲────────┘      │
└───────────────────────┼───────────────────────┼──────────────┘
                        │                       │
                   HTTP POST              HTTP POST
                   (trigger)              (results)
                        │                       │
┌───────────────────────▼───────────────────────┼──────────────┐
│                 PYTHON PIPELINE (Railway/Local)               │
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
│  │ 1. COLLECT   │──▶│ 2. DETECT   │──▶│ 3. ANALYSE      │    │
│  │              │   │              │   │                  │    │
│  │ API Client   │   │ Diff Engine  │   │ Claude API       │    │
│  │ training.    │   │ Baseline     │   │ Scoring          │    │
│  │ gov.au REST  │   │ Compare      │   │ Suggestions      │    │
│  └──────┬──────┘   └──────┬──────┘   └────────┬─────────┘    │
│         │                  │                    │              │
│         ▼                  ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                    SQLite Database                    │     │
│  │  prospects | baselines | trigger_events | news_seen  │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
│  │ 4. DELIVER   │   │ 5. TRAINING  │   │ 6. NEWS         │    │
│  │              │   │    PACKAGES   │   │    MONITOR      │    │
│  │ Format HTML  │   │              │   │                  │    │
│  │ Post to Make │   │ Release check│   │ ASQA scraper     │    │
│  │ webhooks     │   │ Cross-ref    │   │ Relevance filter │    │
│  └─────────────┘   └─────────────┘   └─────────────────┘    │
└───────────────────────────────────────────────────────────────┘
                        │
                   API Calls
                        │
┌───────────────────────▼──────────────────────────────────────┐
│              TRAINING.GOV.AU REST API                          │
│  /api/organisation/{code}/*    /api/training/{code}/*         │
└───────────────────────────────────────────────────────────────┘
```

## 4. Project Structure

```
rto-intel/
├── .env                          # API keys, webhook URLs, config
├── .env.example                  # Template for .env
├── requirements.txt              # Python dependencies
├── README.md                     # Setup and usage instructions
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Pipeline orchestrator (entry point)
│   ├── config.py                 # Environment config loader
│   │
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── tga_client.py         # training.gov.au REST API client
│   │   ├── asqa_monitor.py       # ASQA news scraper
│   │   └── training_monitor.py   # Training package release checker
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── differ.py             # Change detection engine (deepdiff)
│   │   └── events.py             # Trigger event model and categorisation
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── claude_client.py      # Anthropic API client with retry
│   │   └── prompts.py            # Prompt templates for outreach analysis
│   │
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── digest.py             # HTML email formatter
│   │   ├── make_webhook.py       # Make.com webhook poster
│   │   └── sheets_writer.py      # Google Sheets output (via Make.com or gspread)
│   │
│   └── storage/
│       ├── __init__.py
│       ├── database.py           # SQLite schema, migrations, queries
│       └── models.py             # Data models (Prospect, Baseline, TriggerEvent)
│
├── scripts/
│   ├── init_baseline.py          # One-time: full baseline pull
│   ├── load_prospects.py         # Import prospect spreadsheet into DB
│   └── test_api.py               # Quick API endpoint tester
│
├── data/
│   ├── prospects.csv             # Input: prospect spreadsheet
│   └── rto_intel.db              # SQLite database (gitignored)
│
└── tests/
    ├── test_tga_client.py
    ├── test_differ.py
    └── test_prompts.py
```

## 5. Component Design

### 5.1 TGA API Client (`collectors/tga_client.py`)

```python
class TGAClient:
    """training.gov.au REST API client with throttling and error handling."""
    
    BASE_URL = "https://training.gov.au/api"
    RATE_LIMIT = 1.5  # seconds between requests
    MAX_RETRIES = 3
    
    async def get_organisation(self, code: str) -> dict
    async def get_scope(self, code: str) -> dict
    async def get_scope_summary(self, code: str) -> dict
    async def get_regulatory_decisions(self, code: str) -> dict
    async def get_registration(self, code: str) -> dict
    async def get_contacts(self, code: str) -> dict
    async def get_restrictions(self, code: str) -> dict
    async def get_training_component(self, code: str) -> dict
    async def get_training_releases(self, code: str) -> dict
    
    async def get_full_rto_data(self, code: str) -> dict:
        """Fetch all endpoints for an RTO. Returns combined dict."""
```

Design decisions:
- **Async with `httpx.AsyncClient`** for concurrent requests (with semaphore for rate limiting)
- **Throttle via `asyncio.Semaphore` + `asyncio.sleep`** to respect rate limits
- **Exponential backoff retry** for 429, 500, 503 responses
- **Response caching** within a single run (if same RTO queried for multiple purposes)
- Returns raw JSON dicts — no premature data modelling at this layer

### 5.2 Change Detection (`detection/differ.py`)

```python
class ChangeDetector:
    """Compares current API data against stored baseline."""
    
    def detect_changes(self, rto_code: str, current: dict, baseline: dict) -> list[TriggerEvent]:
        """Compare current data with baseline, return list of trigger events."""
    
    def detect_scope_changes(self, current_scope: list, baseline_scope: list) -> list[TriggerEvent]:
        """Scope-specific diffing: additions, removals, status changes."""
    
    def detect_regulatory_changes(self, current: list, baseline: list) -> list[TriggerEvent]:
        """New regulatory decisions not present in baseline."""
    
    def detect_registration_changes(self, current: dict, baseline: dict) -> list[TriggerEvent]:
        """Registration period, status, or manager changes."""
```

Design decisions:
- **`deepdiff` for structural comparison** — handles nested JSON well, produces human-readable diffs
- **Hash-based quick check** — hash full response JSON first; only run detailed diff if hash changed
- **Scope diffing by component code** — treat scope as a keyed collection, not a flat list
- **Regulatory decisions by decision ID or date** — detect new entries

### 5.3 AI Analysis (`analysis/claude_client.py`)

```python
class OutreachAnalyser:
    """Uses Claude API to score trigger events and generate outreach suggestions."""
    
    def analyse_rto_events(self, rto_context: dict, events: list[TriggerEvent]) -> list[TriggerEvent]:
        """Batch-analyse all events for one RTO. Returns events enriched with AI fields."""
```

Design decisions:
- **Batch events per RTO** — one API call per RTO with changes, not per event
- **Structured output via system prompt** — instruct Claude to return JSON with score, opening, implication per event
- **Model selection**: `claude-sonnet-4-5-20250929` for analysis quality; option to use Haiku for high-volume filtering
- **Cost control**: Track token usage per run; alert if exceeding daily budget threshold
- **Prompt includes Jimmy's consulting context** so suggestions are specific to his AI consulting positioning

### 5.4 Delivery (`delivery/digest.py`, `delivery/make_webhook.py`)

Two output channels, both triggered via Make.com webhooks:

**Email Digest:**
- HTML template with inline CSS (email-safe)
- Grouped by RTO, sorted by outreach score
- Summary header with event counts
- Each event: type badge, detail, score indicator, suggested opening

**Structured Data:**
- JSON payload posted to Make.com webhook
- Make.com scenario maps fields to Google Sheets columns
- One row per trigger event

### 5.5 Storage (`storage/database.py`)

SQLite schema:

```sql
CREATE TABLE prospects (
    rto_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT,
    abn TEXT,
    rto_type TEXT,
    web_url TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_checked DATETIME
);

CREATE TABLE baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rto_code TEXT NOT NULL,
    endpoint TEXT NOT NULL,  -- 'scope', 'regulatory', 'registration', etc.
    data_hash TEXT NOT NULL,
    data_json TEXT NOT NULL,  -- full JSON response
    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rto_code, endpoint)
);

CREATE TABLE trigger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    rto_code TEXT NOT NULL,
    rto_name TEXT,
    event_type TEXT NOT NULL,
    event_category TEXT NOT NULL,
    old_value TEXT,  -- JSON
    new_value TEXT NOT NULL,  -- JSON
    outreach_score TEXT,  -- High/Medium/Low (populated by AI)
    suggested_opening TEXT,
    business_implication TEXT,
    source_url TEXT,
    delivery_status TEXT DEFAULT 'pending',
    outreach_status TEXT DEFAULT 'New',
    FOREIGN KEY (rto_code) REFERENCES prospects(rto_code)
);

CREATE TABLE training_baselines (
    component_code TEXT PRIMARY KEY,
    component_type TEXT,
    current_release TEXT,
    status TEXT,
    data_json TEXT,
    checked_at DATETIME,
    rto_codes TEXT  -- JSON array of RTO codes with this on scope
);

CREATE TABLE news_seen (
    url_hash TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevant BOOLEAN DEFAULT FALSE,
    included_in_digest BOOLEAN DEFAULT FALSE
);
```

## 6. Pipeline Execution Flow

```
main.py orchestrates this sequence:

1. LOAD CONFIG
   └── Read .env, validate API keys and webhook URLs

2. LOAD PROSPECTS
   └── Query SQLite for all prospect RTO codes

3. COLLECT DATA (async, throttled)
   ├── For each RTO code:
   │   ├── GET /api/organisation/{code}
   │   ├── GET /api/organisation/{code}/scope
   │   ├── GET /api/organisation/{code}/regulatorydecision
   │   ├── GET /api/organisation/{code}/registration
   │   ├── GET /api/organisation/{code}/contacts
   │   └── GET /api/organisation/{code}/restrictions
   └── Collect errors for retry/logging

4. DETECT CHANGES
   ├── For each RTO with successful API data:
   │   ├── Load baseline from SQLite
   │   ├── Quick hash check (skip detailed diff if unchanged)
   │   ├── Run detailed diff if hash changed
   │   ├── Generate TriggerEvent objects
   │   └── Update baseline with current data
   └── Collect all trigger events

5. MONITOR TRAINING PACKAGES (if any scope changes detected)
   ├── Extract affected training component codes
   ├── Check Training API for release/supersession changes
   └── Cross-reference with prospect scope; generate events

6. MONITOR NEWS
   ├── Scrape ASQA media releases
   ├── Filter for new items (not in news_seen)
   └── Assess relevance via Claude API (lightweight call)

7. AI ANALYSIS
   ├── Group trigger events by RTO
   ├── For each RTO with events:
   │   ├── Build context (RTO details + event list)
   │   ├── Call Claude API for outreach analysis
   │   └── Enrich events with score, opening, implication
   └── Store enriched events in SQLite

8. DELIVER
   ├── Format HTML digest from enriched events
   ├── POST digest to Make.com email webhook
   ├── POST structured events to Make.com sheets webhook
   └── Update delivery_status to 'delivered'

9. LOG & CLEANUP
   ├── Log run summary (RTOs checked, events found, errors)
   └── Cleanup old baseline snapshots if needed
```

## 7. Make.com Integration

### Scenario 1: Daily Trigger (Scheduled)
```
[Schedule: 6:30 AM AEST daily]
    → [HTTP Module: POST to Railway/Render endpoint]
        → Triggers Python pipeline run
```

### Scenario 2: Receive Results (Webhook)
```
[Webhook: Receive digest payload]
    → [Router]
        ├── Route 1: [Gmail: Send digest email to Jimmy]
        └── Route 2: [Google Sheets: Append event rows]
```

Alternative: If running locally via cron, the Python script calls Make.com webhooks directly to send email and write to sheets, eliminating Scenario 1.

## 8. Configuration

```env
# .env file
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

TGA_API_BASE_URL=https://training.gov.au/api
TGA_RATE_LIMIT_SECONDS=1.5

MAKE_WEBHOOK_DIGEST=https://hook.make.com/...
MAKE_WEBHOOK_SHEETS=https://hook.make.com/...

PROSPECTS_FILE=data/prospects.csv
DATABASE_PATH=data/rto_intel.db

LOG_LEVEL=INFO
DAILY_BUDGET_ALERT_USD=5.00
```

## 9. Error Handling Strategy

| Error | Handling |
|-------|---------|
| API 404 (RTO not found) | Log warning, skip RTO, continue pipeline |
| API 429 (rate limited) | Exponential backoff, retry up to 3 times |
| API 500/503 (server error) | Retry with backoff; after 3 failures, skip and log |
| API timeout | Retry once with longer timeout; then skip |
| Claude API error | Retry once; if persistent, deliver events without AI enrichment |
| Make.com webhook failure | Retry once; fall back to local JSON file output |
| Database error | Critical — stop pipeline, alert via stderr/logging |
| Malformed API response | Log full response, skip RTO, continue |

## 10. Security Considerations

- **API keys** stored in `.env`, never committed to git (`.gitignore`)
- **No PII** beyond publicly available training.gov.au data
- **Make.com webhooks** are unique URLs acting as bearer tokens — don't expose
- **SQLite database** is local only; not exposed to network
- **No authentication layer needed** — single user, local execution

## 11. Testing Strategy

- **Unit tests** for change detection logic (mock API responses, verify correct events generated)
- **Integration test** for TGA API client (hit real API with one known RTO code, verify response shape)
- **Prompt testing** — verify Claude API returns parseable JSON with expected fields
- **End-to-end** — run full pipeline against 3-5 test RTOs, verify email digest and sheet output

## 12. Deployment Options

### Option A: Railway (Recommended for Weekend)
- Deploy Python app to Railway free tier
- Expose HTTP endpoint that Make.com calls on schedule
- Pro: Always available, no local machine dependency
- Con: Free tier has limits; may need to manage cold starts

### Option B: Local Cron
- Run pipeline as cron job on Jimmy's machine
- `0 6 * * * cd /path/to/rto-intel && python -m src.main`
- Pro: Zero cost, full control
- Con: Requires machine to be on; no remote trigger

### Option C: GitHub Actions (Clever Free Option)
- Scheduled workflow runs daily
- Store SQLite as artifact or use GitHub Actions cache
- Pro: Free, reliable scheduling, no infrastructure
- Con: Slightly more complex setup; artifact storage limits
