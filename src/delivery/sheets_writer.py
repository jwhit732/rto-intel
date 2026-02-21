"""Google Sheets writer (via Make.com or direct API)."""

import logging
from datetime import datetime
from typing import List

from src.storage.models import TriggerEvent

logger = logging.getLogger(__name__)


def format_events_for_sheets(events: List[TriggerEvent]) -> List[dict]:
    """Format trigger events for Google Sheets.

    Args:
        events: List of TriggerEvent objects

    Returns:
        List of dicts with sheet columns
    """
    rows = []

    for event in events:
        row = {
            "Date": (
                event.detected_at.strftime("%Y-%m-%d %H:%M")
                if event.detected_at
                else datetime.now().strftime("%Y-%m-%d %H:%M")
            ),
            "RTO Code": event.rto_code,
            "RTO Name": event.rto_name,
            "Event Type": event.event_type.replace("_", " ").title(),
            "Event Category": event.event_category,
            "Outreach Score": event.outreach_score or "Low",
            "Suggested Opening": event.suggested_opening or "",
            "Business Implication": event.business_implication or "",
            "Source URL": event.source_url or "",
            "Status": event.outreach_status or "New",
        }
        rows.append(row)

    logger.info(f"Formatted {len(rows)} events for sheets")
    return rows
