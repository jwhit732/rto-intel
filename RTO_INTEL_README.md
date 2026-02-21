# RTO Intel Pipeline

AI-powered intelligence pipeline for monitoring Australian RTOs via the training.gov.au REST API.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your Anthropic API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Load Prospects

Import the top 350 prospects from the spreadsheet into SQLite:

```bash
python scripts/load_prospects.py
```

Expected output:
```
INFO - Loading prospects from prospects\asqa_rtos_scored.xlsx
INFO - Successfully loaded 350 prospects into database
```

### 4. Initialize Baseline

Fetch initial API data for all prospects (takes ~50 minutes for 350 RTOs):

```bash
python scripts/init_baseline.py
```

This creates baseline snapshots for change detection. Only needs to run once, or when you want to reset baselines.

### 5. Run Pipeline

Execute the full monitoring pipeline:

```bash
python -m src.main
```

This will:
1. Fetch current API data for all prospects
2. Detect changes against baseline
3. Analyze changes with Claude AI
4. Generate HTML digest and event data
5. Optionally send to Make.com webhooks

## Output

The pipeline creates:

1. **HTML Digest**: `output/digest_YYYYMMDD_HHMMSS.html`
   - Email-ready summary of all trigger events
   - Grouped by RTO, sorted by priority
   - Open in browser to preview

2. **Events JSON**: `output/events_YYYYMMDD_HHMMSS.json`
   - Structured event data for further processing
   - Can be imported to Google Sheets manually if webhooks not configured

## Project Structure

```
prospect_tracker/
├── src/
│   ├── main.py                    # Pipeline orchestrator
│   ├── config.py                  # Configuration loader
│   ├── collectors/
│   │   └── tga_client.py         # training.gov.au API client
│   ├── detection/
│   │   ├── differ.py             # Change detection engine
│   │   └── events.py             # Event types and categories
│   ├── analysis/
│   │   ├── claude_client.py      # Anthropic API client
│   │   └── prompts.py            # AI prompt templates
│   ├── delivery/
│   │   ├── digest.py             # HTML email formatter
│   │   ├── make_webhook.py       # Make.com integration
│   │   └── sheets_writer.py      # Google Sheets formatter
│   └── storage/
│       ├── database.py           # SQLite interface
│       └── models.py             # Data models
├── scripts/
│   ├── load_prospects.py         # Import prospects from Excel
│   └── init_baseline.py          # Initialize baseline snapshots
├── data/
│   └── rto_intel.db              # SQLite database (created on first run)
├── prospects/
│   └── asqa_rtos_scored.xlsx     # Input spreadsheet
└── output/                        # Generated digests and events
```

## Daily Operation

Once baseline is initialized, run the pipeline daily:

```bash
python -m src.main
```

The pipeline will:
- Check all 350 RTOs against their baselines (~30-40 min with rate limiting)
- Detect and analyze any changes
- Generate digest with actionable outreach suggestions
- Update baselines for next run

## Make.com Integration (Optional)

To automate email delivery and Google Sheets updates:

1. Create Make.com scenario with HTTP webhook trigger
2. Add webhook URLs to `.env`:
   ```
   MAKE_WEBHOOK_DIGEST=https://hook.make.com/...
   MAKE_WEBHOOK_SHEETS=https://hook.make.com/...
   ```

3. Configure Make.com to:
   - Route digest to Gmail
   - Append events to Google Sheets

## Troubleshooting

### "No prospects found"
Run `python scripts/load_prospects.py` first.

### "Required environment variable ANTHROPIC_API_KEY is not set"
Copy `.env.example` to `.env` and add your API key.

### API rate limiting
The client automatically throttles to 1.5 sec/request. For faster runs, reduce `TOP_N_PROSPECTS` in `.env`.

### No changes detected
This is normal if RTOs haven't been updated since baseline initialization. The system will email a "no changes" confirmation.

## Configuration Options

Edit `.env` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `TOP_N_PROSPECTS` | Number of prospects to monitor | 350 |
| `TGA_RATE_LIMIT_SECONDS` | Seconds between API requests | 1.5 |
| `ANTHROPIC_MODEL` | Claude model to use | claude-sonnet-4-5-20250929 |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Architecture Notes

- **SQLite database**: All state stored in `data/rto_intel.db`
- **Baseline snapshots**: Stored per endpoint (scope, regulatory, registration, etc.)
- **Change detection**: Uses `deepdiff` for structural JSON comparison
- **AI analysis**: Batches events per RTO to minimize API calls
- **Rate limiting**: Enforced via async semaphore to respect training.gov.au

## Next Steps

1. **Schedule daily runs**: Use cron, Task Scheduler, or Railway deployment
2. **Set up Make.com**: Automate email and sheets delivery
3. **Customize prompts**: Edit `src/analysis/prompts.py` to tune AI analysis
4. **Add training package monitoring**: Implement Epic 4 (deferred for MVP)
5. **Add ASQA news monitoring**: Implement Epic 6 (deferred for MVP)

## Cost Estimate

- **Claude API**: ~$0.50-2.00 per day (depends on number of changes detected)
- **training.gov.au API**: Free, no authentication required
- **Make.com**: Free tier (1,000 operations/month) covers daily runs
- **Total**: <$60/month for 350 RTOs monitored daily

## Support

For issues or questions:
1. Check logs in console output
2. Review `output/` directory for generated files
3. Test individual components (API client, change detector) in isolation
