"""Weekly RTO Intel pipeline - clean entry point for VPS/cron execution.

Usage:
    python -m src.weekly_run

Outputs:
    output/latest_events.json   - Structured events for OpenClaw
    output/latest_digest.html   - HTML email digest
    output/latest_meta.json     - Run metadata and status
"""

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
from src.storage.database import Database

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


async def run_weekly_pipeline():
    """Execute weekly RTO Intel pipeline.

    Only processes RTOs that have existing baselines.
    Outputs to consistent filenames for OpenClaw consumption.
    """
    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("RTO Intel Weekly Pipeline")
    logger.info(f"Started: {start_time.isoformat()}")
    logger.info("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Initialize database
    db = Database(config.database_path)
    db.connect()
    db.init_schema()

    # Find RTOs with baselines (only process these)
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT rto_code FROM baselines")
    baselined_rtos = [row[0] for row in cursor.fetchall()]

    logger.info(f"Found {len(baselined_rtos)} RTOs with baselines")

    if not baselined_rtos:
        logger.error("No baselines found. Run init_baseline.py first.")
        _write_meta(start_time, "error", "No baselines found", 0, 0, [])
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
    success_count = 0
    error_count = 0
    errors = []

    for index, rto_code in enumerate(baselined_rtos, 1):
        logger.info(f"[{index}/{len(baselined_rtos)}] Processing RTO {rto_code}")

        try:
            prospect = db.get_prospect(rto_code)
            if not prospect:
                logger.warning(f"  Prospect not in database, skipping")
                continue

            # Fetch current data
            current_data = await tga_client.get_full_rto_data(rto_code)

            # Load baselines
            baseline_data = {}
            for endpoint in ["scope", "regulatory", "registration", "contacts", "restrictions"]:
                baseline_data[endpoint] = db.get_baseline(rto_code, endpoint)

            # Detect changes
            events = change_detector.detect_all_changes(
                rto_code, prospect.name, current_data, baseline_data
            )

            if events:
                logger.info(f"  Detected {len(events)} changes")
                all_events.extend(events)
            else:
                logger.info(f"  No changes")

            # Update baselines
            for endpoint, data in current_data.items():
                if data is not None:
                    db.store_baseline(rto_code, endpoint, data)

            db.update_prospect_last_checked(rto_code)

            # Record history snapshot for pattern memory
            scope_data = current_data.get("scope")
            reg_data = current_data.get("registration")
            db.record_rto_snapshot(
                rto_code=rto_code,
                qual_count=prospect.qual_count or 0,
                has_restrictions=bool(current_data.get("restrictions")),
                scope_items=len(scope_data) if isinstance(scope_data, list) else 0,
                regulatory_events=len(events) if events else 0,
                registration_status=reg_data.get("status") if reg_data else None,
            )

            success_count += 1

        except Exception as e:
            logger.error(f"  Error: {e}")
            error_count += 1
            errors.append({"rto_code": rto_code, "error": str(e)})

    logger.info(f"Collection complete: {success_count} success, {error_count} errors")
    logger.info(f"Total changes detected: {len(all_events)}")

    # AI Analysis (if events found)
    enriched_events = []
    if all_events:
        logger.info("Running AI analysis...")

        analyser = OutreachAnalyser(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )

        # Group by RTO
        events_by_rto = {}
        for event in all_events:
            if event.rto_code not in events_by_rto:
                events_by_rto[event.rto_code] = []
            events_by_rto[event.rto_code].append(event)

        # Analyze each RTO's events
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

        logger.info(f"AI analysis complete: {len(enriched_events)} events enriched")

    # Build output with contact info
    events_output = []
    for event in enriched_events:
        prospect = db.get_prospect(event.rto_code)
        events_output.append({
            "rto_code": event.rto_code,
            "rto_name": event.rto_name,
            "industry": prospect.industry if prospect else None,
            "event_type": event.event_type,
            "event_category": event.event_category,
            "outreach_score": event.outreach_score,
            "suggested_opening": event.suggested_opening,
            "business_implication": event.business_implication,
            "source_url": event.source_url,
            # Contact info for OpenClaw
            "contact_name": prospect.contact_name if prospect else None,
            "contact_email": prospect.contact_email if prospect else None,
            "contact_role": prospect.contact_role if prospect else None,
            "contact_phone": prospect.contact_phone if prospect else None,
            "website": prospect.website if prospect else None,
        })

    db.close()

    # Write outputs
    _write_events(events_output)
    _write_digest(enriched_events)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    _write_meta(
        start_time=start_time,
        status="success",
        message=f"Processed {success_count} RTOs, found {len(enriched_events)} events",
        rtos_checked=success_count,
        events_found=len(enriched_events),
        errors=errors,
        duration_seconds=duration,
        events_by_score={
            "high": sum(1 for e in events_output if e["outreach_score"] == "High"),
            "medium": sum(1 for e in events_output if e["outreach_score"] == "Medium"),
            "low": sum(1 for e in events_output if e["outreach_score"] == "Low"),
        }
    )

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline Complete")
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"RTOs checked: {success_count}")
    logger.info(f"Events found: {len(enriched_events)}")
    high = sum(1 for e in events_output if e["outreach_score"] == "High")
    logger.info(f"High priority: {high}")
    logger.info(f"Output: {OUTPUT_DIR}/latest_*.json")
    logger.info("=" * 60)


def _write_events(events: list):
    """Write events to latest_events.json."""
    output = {
        "generated_at": datetime.now().isoformat(),
        "event_count": len(events),
        "events": events,
    }

    path = OUTPUT_DIR / "latest_events.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info(f"Events written to {path}")


def _write_digest(events: list):
    """Write HTML digest to latest_digest.html."""
    html = format_digest(events)
    path = OUTPUT_DIR / "latest_digest.html"
    path.write_text(html, encoding="utf-8")
    logger.info(f"Digest written to {path}")


def _write_meta(
    start_time: datetime,
    status: str,
    message: str,
    rtos_checked: int,
    events_found: int,
    errors: list,
    duration_seconds: float = 0,
    events_by_score: dict = None,
):
    """Write run metadata to latest_meta.json."""
    meta = {
        "run_timestamp": start_time.isoformat(),
        "status": status,
        "message": message,
        "rtos_checked": rtos_checked,
        "events_found": events_found,
        "events_by_score": events_by_score or {"high": 0, "medium": 0, "low": 0},
        "duration_seconds": round(duration_seconds, 1),
        "errors": errors,
        "output_files": {
            "events": "output/latest_events.json",
            "digest": "output/latest_digest.html",
            "meta": "output/latest_meta.json",
        }
    }

    path = OUTPUT_DIR / "latest_meta.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info(f"Metadata written to {path}")


if __name__ == "__main__":
    asyncio.run(run_weekly_pipeline())
