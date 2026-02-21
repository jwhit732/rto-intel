# Product Requirements Document (PRD): RTO Intel Pipeline

## 1. Executive Summary

RTO Intel is a personal AI-powered intelligence pipeline that monitors Australian Registered Training Organisation (RTO) prospects via the training.gov.au REST API, detects actionable changes, analyses them with Claude AI, and delivers daily briefings to support informed sales outreach.

## 2. Goals and Non-Goals

### Goals
- Automate daily collection of RTO data for 50-200 prospects from training.gov.au REST API
- Detect and categorise changes against a stored baseline (scope, regulatory, registration, contacts)
- Use Claude API to score outreach relevance and generate suggested conversation openers
- Deliver a morning email digest and populate a structured outreach queue (Google Sheets/Airtable)
- Run reliably on a daily schedule without manual intervention
- Be buildable in a weekend (~16 hours of focused work)

### Non-Goals
- Multi-user SaaS platform (single user only)
- Web UI or dashboard (CLI + automated delivery only)
- Automated outbound email sending
- SOAP API integration (REST-first; SOAP is a future enhancement)
- Real-time monitoring (daily batch is sufficient)
- Historical analytics or trend visualisation

## 3. User Stories

### US-1: Daily Trigger Event Detection
**As** Jimmy, **I want** the system to automatically check my prospect list against training.gov.au daily, **so that** I know when something changes at any of my target RTOs without manually checking each one.

**Acceptance Criteria:**
- System iterates through all RTO codes from the prospect spreadsheet
- Calls Organisation API endpoints for each RTO (scope, regulatory decisions, registration, contacts)
- Compares current API response against stored baseline
- Identifies and records all differences as "trigger events"
- Handles API errors gracefully (timeouts, 404s, rate limits) without stopping the full run

### US-2: AI-Powered Outreach Analysis
**As** Jimmy, **I want** each trigger event to be analysed by AI for its outreach relevance, **so that** I can prioritise which prospects to contact and know what to say.

**Acceptance Criteria:**
- Each trigger event is sent to Claude API with context about the RTO and the type of change
- AI assigns an outreach score: High, Medium, or Low
- AI generates a 1-2 sentence suggested opening that demonstrates awareness of the change
- AI explains the business/compliance implication of the change in 1-2 sentences
- Events are batched per RTO to minimise API calls (one call per RTO with changes, not per event)

### US-3: Morning Email Digest
**As** Jimmy, **I want** a summary email delivered before 8am AEST each morning, **so that** I can review trigger events over coffee and plan my outreach for the day.

**Acceptance Criteria:**
- Email sent via Make.com (Gmail or SMTP integration)
- Grouped by prospect (RTO name and code)
- Each event shows: event type, what changed, outreach score, suggested opening
- Events sorted by outreach score (High first)
- If no events detected, send a brief "no changes today" confirmation
- Include count summary at top (e.g., "3 High, 5 Medium, 2 Low priority events across 7 RTOs")

### US-4: Structured Outreach Queue
**As** Jimmy, **I want** trigger events written to a Google Sheet or Airtable, **so that** I can filter, sort, and track my outreach status for each event.

**Acceptance Criteria:**
- One row per trigger event
- Columns: Date, RTO Code, RTO Name, Event Type, Event Category (Scope/Regulatory/Registration/Contact), Event Detail, Outreach Score, Suggested Opening, Business Implication, Source URL, Status (New)
- New events appended; existing rows not modified
- Status column defaults to "New" for manual tracking (Contacted, Dismissed, etc.)

### US-5: Training Package Change Monitoring
**As** Jimmy, **I want** to know when training packages that my prospects deliver are being updated or superseded, **so that** I can proactively reach out about transition needs before they realise they have a problem.

**Acceptance Criteria:**
- System maintains a list of unique training packages across all prospect scopes
- Checks Training API for release changes and supersession mappings
- Cross-references affected packages against prospect scope data
- Generates trigger events for each affected prospect-package combination

### US-6: Baseline Initialisation
**As** Jimmy, **I want** to run an initial data pull that captures the current state of all prospects, **so that** subsequent runs can detect what has changed.

**Acceptance Criteria:**
- Script reads prospect spreadsheet and extracts RTO codes
- Calls all relevant API endpoints for each RTO
- Stores complete response data as JSON baseline
- Baseline stored locally (SQLite or JSON files) with timestamp
- Can be re-initialised on demand (overwrite existing baseline)
- Provides progress feedback during initial pull (can take several minutes for 50+ RTOs)

### US-7: ASQA News Monitoring
**As** Jimmy, **I want** to be alerted to ASQA regulatory announcements and policy changes, **so that** I can reference industry developments in my outreach.

**Acceptance Criteria:**
- Monitors ASQA website for new media releases
- Passes new items through Claude API to assess relevance to RTO consulting
- Includes relevant items in daily digest under "Industry News" section
- Stores seen items to avoid re-alerting

## 4. Functional Requirements

### FR-1: Data Collection Engine
- Read prospect list from CSV/Excel file
- Extract RTO codes as lookup keys
- Call training.gov.au REST API endpoints (no authentication required):
  - `/api/organisation/{code}` — org details
  - `/api/organisation/{code}/scope` — full scope
  - `/api/organisation/{code}/scopesummary` — scope summary
  - `/api/organisation/{code}/regulatorydecision` — regulatory decisions
  - `/api/organisation/{code}/registration` — registration period
  - `/api/organisation/{code}/contacts` — contacts
  - `/api/organisation/{code}/restrictions` — restrictions
- Implement request throttling (1-2 requests/second) to respect the API
- Handle HTTP errors, timeouts, and malformed responses
- Log all API interactions for debugging

### FR-2: Change Detection Engine
- Load previous baseline snapshot
- Compare current API response with baseline for each field
- Categorise changes:
  - **Scope changes**: New items added, items removed, status changes on existing items
  - **Regulatory decisions**: New decisions not in baseline
  - **Registration changes**: Status change, expiry date change, registration manager change
  - **Contact changes**: New contacts, removed contacts, changed details
  - **Restriction changes**: New restrictions, removed restrictions
- Generate structured trigger event objects with: timestamp, rto_code, rto_name, event_type, event_category, old_value, new_value, raw_data
- Update baseline with current data after comparison

### FR-3: AI Analysis Engine
- Batch trigger events by RTO
- Construct Claude API prompts with:
  - RTO context (name, type, size indicators from scope breadth)
  - List of changes detected
  - Jimmy's consulting focus (AI solutions for compliance, training resource development, workflow automation)
- Parse Claude API response to extract:
  - Outreach score per event (High/Medium/Low)
  - Suggested opening (1-2 sentences)
  - Business implication (1-2 sentences)
- Use claude-sonnet-4-5-20250929 for analysis (balance of quality and cost)
- Implement retry logic for API failures

### FR-4: Delivery Engine
- **Email digest**: Format trigger events as HTML email, send via Make.com webhook
- **Structured data**: Write events to Google Sheets via Make.com or direct API
- **Make.com scenario**: HTTP webhook trigger → process data → send email + write to sheet

### FR-5: Training Package Monitor
- Extract unique training component codes from all prospect scopes
- Call `/api/training/{code}` and `/api/training/{code}/releases` for each
- Detect new releases, supersession events
- Cross-reference with prospect scope data to identify affected RTOs
- Generate trigger events linked to specific prospects

### FR-6: External News Monitor
- Scrape or RSS-poll ASQA media releases page
- Store seen items (URL or title hash) to detect new ones
- Pass new items through Claude API for relevance assessment
- Include in daily digest if relevant

## 5. Non-Functional Requirements

### NFR-1: Performance
- Full pipeline run completes in < 30 minutes for 100 RTOs
- API calls throttled to 1-2 per second to avoid overwhelming training.gov.au
- Email digest delivered by 8:00 AM AEST daily

### NFR-2: Reliability
- Graceful error handling — individual RTO failures don't stop the full run
- Retry logic for transient API failures (3 retries with exponential backoff)
- Daily run logging with clear error reporting
- Pipeline should recover from previous failed runs without data corruption

### NFR-3: Cost
- Claude API costs < $5/day for typical usage (50-100 RTOs, ~10-20 events/day)
- Make.com within free tier (1,000 operations/month) or low-cost tier
- Hosting free or < $10/month (Railway/Render free tier, or local cron)

### NFR-4: Maintainability
- Clean Python code with clear module separation
- Configuration via environment variables or .env file
- Prospect list easily updateable (replace CSV)
- Logging sufficient to diagnose issues without debugging code

### NFR-5: Data Storage
- SQLite database for baseline storage (portable, no server required)
- JSON files as fallback/export format
- No PII beyond what's publicly available on training.gov.au

## 6. Technical Assumptions

1. The training.gov.au REST API endpoints visible in Swagger are publicly accessible without authentication
2. The REST API returns JSON responses matching the schemas documented in Swagger
3. API rate limits (if any) are reasonable for polling 50-200 RTOs daily
4. Make.com free tier provides sufficient operations for daily digest + sheet writes
5. Claude API (Sonnet) provides sufficient quality for outreach analysis at reasonable cost
6. training.gov.au data updates propagate to the API within 24 hours

## 7. Data Model

### Prospect
```
rto_code: string (primary key)
name: string
status: string
abn: string
contacts: JSON
addresses: JSON
web_url: string
last_checked: datetime
```

### Baseline Snapshot
```
rto_code: string (FK)
endpoint: string (scope|regulatory|registration|contacts|restrictions)
data_hash: string (for quick change detection)
data_json: JSON (full response)
captured_at: datetime
```

### Trigger Event
```
id: auto-increment
detected_at: datetime
rto_code: string (FK)
rto_name: string
event_type: string (scope_added|scope_removed|regulatory_new|registration_change|contact_change|restriction_change|package_update|industry_news)
event_category: string (Scope|Regulatory|Registration|Contact|Restriction|Training|News)
old_value: JSON (nullable)
new_value: JSON
outreach_score: string (High|Medium|Low) — populated by AI
suggested_opening: text — populated by AI
business_implication: text — populated by AI
source_url: string
delivery_status: string (pending|delivered)
outreach_status: string (New|Contacted|Dismissed)
```

### Training Component Baseline
```
component_code: string (primary key)
component_type: string (qualification|unit|skillset|package)
current_release: string
status: string
data_json: JSON
checked_at: datetime
rto_codes: JSON (list of prospect RTOs that have this on scope)
```

## 8. Epic Breakdown

### Epic 1: Foundation & Data Collection
Set up project structure, database, prospect loading, and basic API integration with training.gov.au.
- Story 1.1: Project scaffolding (Python project, dependencies, config)
- Story 1.2: Prospect spreadsheet parser
- Story 1.3: training.gov.au REST API client with throttling and error handling
- Story 1.4: SQLite database schema and data access layer
- Story 1.5: Baseline initialisation script (full pull for all prospects)

### Epic 2: Change Detection Engine
Compare current API data against baseline to identify trigger events.
- Story 2.1: Scope change detector (additions, removals, status changes)
- Story 2.2: Regulatory decision detector (new decisions)
- Story 2.3: Registration change detector (status, expiry, manager)
- Story 2.4: Contact and restriction change detector
- Story 2.5: Trigger event storage and deduplication

### Epic 3: AI Analysis Engine
Process trigger events through Claude API for outreach scoring and suggestions.
- Story 3.1: Claude API integration with retry logic
- Story 3.2: Prompt engineering for outreach analysis (per-RTO batching)
- Story 3.3: Response parsing and trigger event enrichment
- Story 3.4: Cost monitoring and Haiku fallback for high-volume days

### Epic 4: Training Package Monitor
Track training package changes that affect prospect scope.
- Story 4.1: Extract unique training components from prospect scopes
- Story 4.2: Training API client for release and supersession checking
- Story 4.3: Cross-reference engine (package changes → affected prospects)
- Story 4.4: Generate prospect-specific trigger events for package changes

### Epic 5: Delivery & Orchestration
Email digest, structured data output, and Make.com integration for scheduling.
- Story 5.1: Email digest template and HTML formatter
- Story 5.2: Make.com webhook integration (trigger pipeline + receive results)
- Story 5.3: Google Sheets / Airtable writer for outreach queue
- Story 5.4: Daily orchestration script (runs all components in sequence)
- Story 5.5: Make.com scenario for scheduling and delivery

### Epic 6: External News Monitoring
Monitor ASQA and industry sources for relevant news.
- Story 6.1: ASQA media release scraper/RSS monitor
- Story 6.2: News relevance filtering via Claude API
- Story 6.3: Integration with digest and outreach queue

## 9. Dependencies

| Component | Dependency | Notes |
|-----------|-----------|-------|
| Data collection | training.gov.au REST API | Must be accessible without auth |
| AI analysis | Anthropic Claude API | API key required, pay-per-use |
| Orchestration | Make.com | Free tier; webhook + Gmail + Sheets modules |
| Delivery | Gmail/SMTP | Via Make.com |
| Structured output | Google Sheets or Airtable | Via Make.com or direct API |
| Hosting (optional) | Railway/Render | For scheduled execution if not using local cron |

## 10. Open Questions

1. **REST API authentication** — Are the new REST endpoints truly open, or will we hit a 401? First task on Saturday is to test with a simple curl request.
2. **Rate limits** — What are the rate limits on the new REST API? Need to test and adjust throttling accordingly.
3. **Data freshness** — How frequently is the API data updated? Daily? Real-time? Affects how often we should poll.
4. **Scope data structure** — What does the `/api/organisation/{code}/scope` response actually look like? Need to inspect to build accurate diffing logic.
5. **Make.com operation count** — Will a daily run for 100 RTOs stay within free tier limits, or do we need a paid plan?
