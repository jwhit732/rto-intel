"""Test pipeline on RTOs that have baselines only."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.claude_client import OutreachAnalyser
from src.collectors.tga_client import TGAClient
from src.config import config
from src.detection.differ import ChangeDetector
from src.delivery.digest import format_digest
from src.storage.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_test_pipeline():
    """Run pipeline only on RTOs that have baselines."""
    logger.info("=" * 60)
    logger.info("Test Pipeline - RTOs with Baselines Only")
    logger.info("=" * 60)

    db = Database(config.database_path)
    db.connect()

    # Find RTOs with baselines
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT rto_code FROM baselines")
    baselined_rtos = [row[0] for row in cursor.fetchall()]

    logger.info(f"Found {len(baselined_rtos)} RTOs with baselines: {baselined_rtos}")

    if not baselined_rtos:
        logger.error("No baselines found. Run init_baseline.py first.")
        db.close()
        return

    # Initialize components
    tga_client = TGAClient(
        base_url=config.tga_api_base_url,
        rate_limit_seconds=config.tga_rate_limit_seconds,
    )
    change_detector = ChangeDetector()

    # Process each RTO
    all_events = []
    for index, rto_code in enumerate(baselined_rtos, 1):
        logger.info(f"[{index}/{len(baselined_rtos)}] Processing RTO {rto_code}")

        prospect = db.get_prospect(rto_code)
        if not prospect:
            logger.warning(f"Prospect {rto_code} not in database")
            continue

        # Fetch current data
        current_data = await tga_client.get_full_rto_data(rto_code)

        # Load baselines
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

        # Update baselines
        for endpoint, data in current_data.items():
            if data is not None:
                db.store_baseline(rto_code, endpoint, data)

        db.update_prospect_last_checked(rto_code)

    logger.info(f"\nTotal events detected: {len(all_events)}")

    # AI Analysis
    if all_events:
        logger.info("Running AI analysis...")

        analyser = OutreachAnalyser(
            api_key=config.anthropic_api_key, model=config.anthropic_model
        )

        # Group by RTO
        events_by_rto = {}
        for event in all_events:
            if event.rto_code not in events_by_rto:
                events_by_rto[event.rto_code] = []
            events_by_rto[event.rto_code].append(event)

        enriched_events = []
        for rto_code, rto_events in events_by_rto.items():
            prospect = db.get_prospect(rto_code)
            rto_context = {
                "rto_code": rto_code,
                "name": prospect.name if prospect else "Unknown",
                "industry": prospect.industry if prospect else "Unknown",
                "qual_count": prospect.qual_count if prospect else 0,
            }

            enriched = analyser.analyse_rto_events(rto_context, rto_events)
            enriched_events.extend(enriched)

            # Store in database
            for event in enriched:
                db.insert_trigger_event(event)

        # Generate digest
        html_digest = format_digest(enriched_events)

        # Save outputs
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        digest_file = output_dir / f"test_digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        digest_file.write_text(html_digest, encoding="utf-8")
        logger.info(f"\nDigest saved: {digest_file}")

        # Summary
        high = sum(1 for e in enriched_events if e.outreach_score == "High")
        medium = sum(1 for e in enriched_events if e.outreach_score == "Medium")
        low = sum(1 for e in enriched_events if e.outreach_score == "Low")

        logger.info(f"Priority: {high} High, {medium} Medium, {low} Low")

    else:
        logger.info("No changes detected - pipeline working correctly!")

    db.close()
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_test_pipeline())
