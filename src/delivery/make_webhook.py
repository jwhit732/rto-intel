"""Make.com webhook integration."""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


async def post_to_webhook(url: str, data: Dict[str, Any]) -> bool:
    """Post data to Make.com webhook.

    Args:
        url: Webhook URL
        data: JSON payload

    Returns:
        True if successful, False otherwise
    """
    if not url:
        logger.warning("Webhook URL not configured, skipping")
        return False

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, json=data, headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 201, 202):
                logger.info(f"Successfully posted to webhook: {url[:50]}...")
                return True
            else:
                logger.error(
                    f"Webhook returned {response.status_code}: {response.text[:200]}"
                )
                return False

    except Exception as e:
        logger.error(f"Error posting to webhook: {e}")
        return False


async def send_digest(webhook_url: str, html_content: str, metadata: Dict) -> bool:
    """Send email digest via Make.com webhook.

    Args:
        webhook_url: Make.com webhook URL
        html_content: HTML email content
        metadata: Additional metadata (event counts, etc.)

    Returns:
        True if successful
    """
    payload = {
        "type": "digest",
        "html": html_content,
        "metadata": metadata,
    }

    return await post_to_webhook(webhook_url, payload)


async def send_events_to_sheets(
    webhook_url: str, events: List[Dict[str, Any]]
) -> bool:
    """Send trigger events to Google Sheets via Make.com webhook.

    Args:
        webhook_url: Make.com webhook URL
        events: List of event dictionaries

    Returns:
        True if successful
    """
    payload = {"type": "events", "events": events}

    return await post_to_webhook(webhook_url, payload)
