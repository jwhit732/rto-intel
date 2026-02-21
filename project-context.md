# Project Context: RTO Intel Pipeline

## Project Type
Data pipeline / automation tool — NOT a web application. No frontend, no UI framework, no user-facing interface beyond email digests.

## Technology Rules

### Python
- Python 3.11+ required
- Use `httpx` for HTTP (not `requests`) — async support matters for API throttling
- Use stdlib `sqlite3` — no SQLAlchemy or ORM overhead for this project size
- Use `asyncio` for concurrent API calls with semaphore-based rate limiting
- Use `python-dotenv` for config — `.env` file, not YAML or TOML config
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- f-strings preferred over `.format()` or `%`

### Dependencies (keep minimal)
- `httpx` — HTTP client
- `anthropic` — Claude API SDK
- `python-dotenv` — env config
- `deepdiff` — JSON comparison
- `beautifulsoup4` — HTML parsing (ASQA scraper only)
- `openpyxl` or `pandas` — spreadsheet reading (prospect import only)
- No framework (no Flask, FastAPI, Django) unless deployment requires an HTTP endpoint

### Code Style
- Module-per-concern structure (see architecture.md project tree)
- No classes where a function will do — prefer functions for stateless operations
- Classes for stateful components (TGAClient, ChangeDetector, OutreachAnalyser, Database)
- Keep files under 200 lines where possible — split if growing
- Error handling: catch specific exceptions, log context, continue pipeline where safe

### Data
- SQLite for all persistence — single file at `data/rto_intel.db`
- JSON for API response storage (TEXT columns in SQLite)
- CSV for prospect import
- No cloud database, no Redis, no message queue

### Testing
- `pytest` for testing
- Mock external APIs in tests (training.gov.au, Anthropic)
- At least one real API integration test (marked with `@pytest.mark.integration`)

## Implementation Preferences

### Naming
- Snake_case for everything Python (files, functions, variables)
- Descriptive names over abbreviations (`regulatory_decisions` not `reg_dec`)
- Constants in UPPER_SNAKE_CASE

### Error Philosophy
- Individual RTO failures must never crash the pipeline
- Log errors with full context (RTO code, endpoint, HTTP status, response body)
- Distinguish retryable errors (429, 500, timeout) from permanent errors (404, 400)
- At end of run, summarise: "Checked 97/100 RTOs. 3 failed: [codes]. 12 trigger events detected."

### AI Prompting
- System prompt defines Jimmy's consulting context and scoring rubric
- User prompt contains RTO-specific data and events
- Always request JSON output with explicit schema
- Parse AI responses defensively — if JSON parsing fails, log and skip enrichment (deliver events un-enriched rather than not at all)

### Delivery
- Make.com webhooks for email and sheets — keep Python responsible for data, Make.com responsible for delivery plumbing
- HTML email uses inline CSS only (no external stylesheets)
- If Make.com is down, write results to local JSON file as fallback

## What NOT To Build
- No web server unless deployment requires it (prefer cron/scheduled trigger)
- No user authentication or multi-tenancy
- No frontend or dashboard
- No real-time streaming — daily batch is the design
- No Docker unless deployment platform requires it
- No CI/CD pipeline (weekend project; manual deploy is fine)
