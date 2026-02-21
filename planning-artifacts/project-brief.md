# Project Brief: RTO Intelligence Pipeline

## Project Name
**RTO Intel** — Automated Intelligence Pipeline for Australian RTO Prospect Monitoring

## Problem Statement

Jimmy runs an AI consulting business targeting Australian Registered Training Organisations (RTOs). His outreach has suffered from low response rates because cold emails lack context about what's actually happening at each prospect's organisation. The information needed to make outreach timely and relevant — scope changes, regulatory decisions, training package updates, registration renewals — is publicly available on training.gov.au, but nobody is systematically monitoring it for sales intelligence purposes.

The gap: there is no tool that watches a list of RTO prospects and surfaces actionable trigger events that create natural outreach opportunities.

## Vision

A personal AI-powered intelligence pipeline that automatically monitors Jimmy's RTO prospect list against training.gov.au data, detects changes and trigger events, analyses them for outreach relevance using AI, and delivers a daily actionable briefing.

## Target User

Solo user (Jimmy). This is a personal productivity tool, not a multi-tenant SaaS product. However, the architecture should be clean enough that it could be packaged as a product for other RTO consultants later.

## Core Value Proposition

Transform cold outreach into warm, contextually-informed engagement by knowing what's happening at each prospect's organisation before they tell you.

## Key Objectives

1. **Automated data collection** — Daily pull of RTO data from training.gov.au REST API for all prospects on the spreadsheet
2. **Change detection** — Compare current state against baseline to identify what changed (scope additions/removals, regulatory decisions, registration status changes)
3. **AI-powered analysis** — Use Claude API to assess each change for outreach relevance and draft suggested opening angles
4. **Supplementary intelligence** — Monitor ASQA news, training package updates, and industry developments that affect prospects
5. **Actionable delivery** — Daily digest delivered in a format that feeds directly into outreach workflow (email digest + structured data in Airtable/Google Sheets)

## Information Sources

### Primary: training.gov.au REST API (New, Open, No Auth Required)
- `GET /api/organisation/{code}` — Full org details, status
- `GET /api/organisation/{code}/scope` — Qualifications, units on scope
- `GET /api/organisation/{code}/scopesummary` — Lightweight scope overview
- `GET /api/organisation/{code}/regulatorydecision` — Audit outcomes, compliance decisions
- `GET /api/organisation/{code}/registration` — Registration periods, renewal dates
- `GET /api/organisation/{code}/contacts` — Key personnel
- `GET /api/organisation/{code}/restrictions` — Registration restrictions
- `GET /api/organisation/{code}/deliverynotificationhistory/{trainingcode}` — Change history per training product

### Secondary: training.gov.au REST API (Training Components)
- `GET /api/training/{code}` — Training component details + mapping info
- `GET /api/training/{code}/releases` — Release history for detecting superseded qualifications
- `GET /api/training/{code}/delivery` — Which RTOs deliver a given component

### Tertiary: External Sources
- ASQA media releases and regulatory updates (RSS/web scrape)
- Training package development schedule (published on training.gov.au homepage)
- Google News alerts for RTO-related keywords

### Fallback: SOAP API (Authenticated)
- Sandbox credentials available (WebService.Read / Asdf098)
- `SearchByModifiedDate` endpoint for efficient delta detection across all RTOs
- Production access requires application to tgaproject@dewr.gov.au
- Architecture note: SOAP provides delta sync capability the REST API may lack

## Input Data

- **Prospect spreadsheet** — Scraped from training.gov.au, contains RTO codes, names, contact details, scope information at time of scrape
- Format: CSV/Excel
- Key fields: RTO code (primary key for API lookups), organisation name, contact details, current scope

## Trigger Events (Prioritised)

### High Outreach Value
1. **Regulatory decisions** — New audit outcomes, compliance conditions, sanctions → "I noticed your recent audit — our AI tools help RTOs streamline compliance documentation"
2. **Scope additions** — New qualifications added → "Congratulations on expanding into [area] — do you have training resources ready?"
3. **Training package supersession** — Quals they deliver are being updated → "The [package] is being reviewed — here's how AI can help you transition your materials"

### Medium Outreach Value
4. **Registration renewal approaching** — Within 6 months of expiry → "With renewal coming up, is your evidence portfolio ready?"
5. **Scope removals** — Qualifications dropped → May indicate strategic shift worth understanding
6. **New delivery locations** — Address changes → Expansion signal

### Lower but Useful
7. **Contact changes** — New key personnel → New decision maker to approach
8. **Status changes** — Registration lapsing or reinstated
9. **Industry news** — ASQA policy changes, funding announcements

## Desired Output

### Daily Email Digest
- Summary of all trigger events detected in the last 24 hours
- Grouped by prospect
- Each event includes: what changed, why it matters, suggested outreach angle
- Link to full details in structured data store

### Structured Data (Airtable or Google Sheets)
- One row per trigger event
- Columns: Date, RTO Code, RTO Name, Event Type, Event Detail, Outreach Score (High/Medium/Low), Suggested Opening, Source URL, Status (New/Contacted/Dismissed)
- Filterable and sortable for daily outreach planning

## Technical Constraints

- **Weekend project** — Must be buildable in ~2 days
- **Budget-conscious** — Prefer free tiers where possible (Make.com free tier, Anthropic API pay-per-use, free hosting)
- **Python primary language** — For scraping/data processing scripts
- **Make.com for orchestration** — Scheduling, API calls, delivery routing
- **Claude API for analysis** — Anthropic API for intelligence analysis
- **Deployment** — Scripts on Railway/Render (free tier) or local cron initially

## Success Criteria

1. Pipeline runs daily without manual intervention
2. Correctly detects at least 3 types of trigger events (scope change, regulatory decision, registration status)
3. AI analysis produces actionable outreach suggestions, not generic summaries
4. Daily digest arrives before 8am AEST
5. End-to-end latency from data collection to delivery < 30 minutes
6. Can monitor at least 50 RTOs without hitting rate limits or excessive API costs

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| REST API requires auth we don't know about | Blocks primary data source | Fall back to SOAP API with existing sandbox credentials; test REST endpoints first |
| REST API rate limiting | Can't poll all prospects daily | Implement backoff; batch requests; cache aggressively |
| training.gov.au data doesn't change often enough | Pipeline produces empty digests | Add external sources (ASQA news, training package schedule) to ensure regular value |
| AI analysis costs add up | Budget overrun | Batch events into single API calls; use Haiku for filtering, Sonnet for analysis |
| Make.com free tier limitations | Orchestration bottleneck | Keep Make.com scenarios simple; do heavy lifting in Python scripts |

## Out of Scope (for this weekend)

- Multi-user support or authentication
- Web UI or dashboard
- Historical trend analysis
- Automated email sending (digest is for Jimmy to act on manually)
- SOAP API integration (REST first, SOAP later if needed)
- LinkedIn monitoring of prospect organisations
- Automated CRM integration

## Future Possibilities

- Package as a product for other RTO consultants
- Add SOAP API `SearchByModifiedDate` for more efficient change detection
- Build a simple web dashboard for browsing trigger events
- Integrate with CRM (HubSpot, Pipedrive) for automated pipeline updates
- Add LinkedIn monitoring for prospect activity
- Expand beyond RTOs to monitor training package developers and regulators
