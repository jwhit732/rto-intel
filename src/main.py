"""Main pipeline orchestrator for RTO Intel."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from src.analysis.claude_client import OutreachAnalyser
from src.collectors.tga_client import TGAClient
from src.config import config
from src.detection.differ import ChangeDetector
from src.delivery.digest import format_digest
from src.delivery.make_webhook import send_digest, send_events_to_sheets
from src.delivery.sheets_writer import format_events_for_sheets
from src.storage.database import Database
from src.storage.models import TriggerEvent

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_pipeline():
    """Execute the full RTO Intel pipeline."""
    logger.info("=" * 60)
    logger.info("Starting RTO Intel Pipeline")
    logger.info("=" * 60)

    start_time = datetime.now()

    # Initialize components
    db = Database(config.database_path)
    db.connect()
    db.init_schema()

    tga_client = TGAClient(
        base_url=config.tga_api_base_url,
        rate_limit_seconds=config.tga_rate_limit_seconds,
    )

    change_detector = ChangeDetector()

    # PHASE 1: Load prospects
    logger.info("PHASE 1: Loading prospects")
    prospect_codes = db.get_all_prospect_codes()
    logger.info(f"Found {len(prospect_codes)} prospects to monitor")

    if not prospect_codes:
        logger.error("No prospects found. Run load_prospects.py first.")
        db.close()
        return

    # PHASE 2: Collect current data and detect changes
    logger.info("PHASE 2: Collecting data and detecting changes")

    all_events = []
    success_count = 0
    error_count = 0

    for index, rto_code in enumerate(prospect_codes, start=1):
        logger.info(f"[{index}/{len(prospect_codes)}] Processing RTO {rto_code}")

        try:
            # Get prospect details
            prospect = db.get_prospect(rto_code)
            if not prospect:
                logger.warning(f"Prospect {rto_code} not found in database")
                continue

            # Fetch current API data
            current_data = await tga_client.get_full_rto_data(rto_code)

            # Load baseline data
            baseline_data = {}
            for endpoint in ["scope", "regulatory", "registration", "contacts", "restrictions"]:
                baseline = db.get_baseline(rto_code, endpoint)
                baseline_data[endpoint] = baseline

            # Detect changes
            events = change_detector.detect_all_changes(
                rto_code, prospect.name, current_data, baseline_data
            )

            if events:
                logger.info(f"  Detected {len(events)} changes")
                all_events.extend(events)
            else:
                logger.info(f"  No changes detected")

            # Update baseline with current data
            for endpoint, data in current_data.items():
                if data is not None:
                    db.store_baseline(rto_code, endpoint, data)

            # Update last_checked timestamp
            db.update_prospect_last_checked(rto_code)

            success_count += 1

        except Exception as e:
            logger.error(f"  Error processing RTO {rto_code}: {e}")
            error_count += 1
            continue

    logger.info(
        f"Data collection complete: {success_count} successful, {error_count} errors"
    )
    logger.info(f"Total changes detected: {len(all_events)}")

    # PHASE 3: AI Analysis (if events found)
    if all_events:
        logger.info("PHASE 3: AI analysis of trigger events")

        # Group events by RTO for batched analysis
        events_by_rto = {}
        for event in all_events:
            if event.rto_code not in events_by_rto:
                events_by_rto[event.rto_code] = []
            events_by_rto[event.rto_code].append(event)

        # Analyze each RTO's events
        analyser = OutreachAnalyser(
            api_key=config.anthropic_api_key, model=config.anthropic_model
        )

        enriched_events = []
        for rto_code, rto_events in events_by_rto.items():
            logger.info(f"Analyzing {len(rto_events)} events for RTO {rto_code}")

            # Get prospect context
            prospect = db.get_prospect(rto_code)
            rto_context = {
                "rto_code": rto_code,
                "name": prospect.name if prospect else "Unknown",
                "industry": prospect.industry if prospect else "Unknown",
                "qual_count": prospect.qual_count if prospect else 0,
            }

            # Analyze and enrich
            enriched = analyser.analyse_rto_events(rto_context, rto_events)
            enriched_events.extend(enriched)

        # Store enriched events in database
        for event in enriched_events:
            db.insert_trigger_event(event)

        logger.info(f"AI analysis complete: {len(enriched_events)} events enriched")

    else:
        logger.info("PHASE 3: Skipped (no changes detected)")
        enriched_events = []

    # PHASE 4: Delivery
    logger.info("PHASE 4: Preparing delivery")

    # Format HTML digest
    html_digest = format_digest(enriched_events)

    # Count events by score
    high_count = sum(1 for e in enriched_events if e.outreach_score == "High")
    medium_count = sum(1 for e in enriched_events if e.outreach_score == "Medium")
    low_count = sum(1 for e in enriched_events if e.outreach_score == "Low")

    metadata = {
        "date": datetime.now().isoformat(),
        "total_events": len(enriched_events),
        "high_priority": high_count,
        "medium_priority": medium_count,
        "low_priority": low_count,
        "rtos_checked": success_count,
        "errors": error_count,
    }

    # Save digest to file (fallback)
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    digest_file = output_dir / f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    digest_file.write_text(html_digest, encoding="utf-8")
    logger.info(f"Digest saved to {digest_file}")

    # Send to Make.com webhooks
    if config.make_webhook_digest:
        logger.info("Sending digest via webhook")
        success = await send_digest(config.make_webhook_digest, html_digest, metadata)
        if success:
            logger.info("Digest delivered successfully")
        else:
            logger.warning("Digest delivery failed")

    if config.make_webhook_sheets and enriched_events:
        logger.info("Sending events to Google Sheets")
        events_data = format_events_for_sheets(enriched_events)
        success = await send_events_to_sheets(config.make_webhook_sheets, events_data)
        if success:
            logger.info("Events delivered to sheets successfully")
        else:
            logger.warning("Sheets delivery failed")

    # Save events to JSON (fallback)
    if enriched_events:
        events_file = (
            output_dir / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        events_data = [
            {
                "rto_code": e.rto_code,
                "rto_name": e.rto_name,
                "event_type": e.event_type,
                "event_category": e.event_category,
                "outreach_score": e.outreach_score,
                "suggested_opening": e.suggested_opening,
                "business_implication": e.business_implication,
                "source_url": e.source_url,
            }
            for e in enriched_events
        ]
        events_file.write_text(json.dumps(events_data, indent=2), encoding="utf-8")
        logger.info(f"Events saved to {events_file}")

    # Close database
    db.close()

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info("Pipeline Complete")
    logger.info(f"Duration: {elapsed:.1f} seconds")
    logger.info(f"RTOs checked: {success_count}/{len(prospect_codes)}")
    logger.info(f"Changes detected: {len(enriched_events)}")
    logger.info(
        f"Priority breakdown: {high_count} High, {medium_count} Medium, {low_count} Low"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
