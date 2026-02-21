"""HTML email digest formatter."""

from datetime import datetime
from typing import Dict, List

from src.storage.models import TriggerEvent


def format_digest(events: List[TriggerEvent]) -> str:
    """Format trigger events as HTML email digest.

    Args:
        events: List of enriched trigger events

    Returns:
        HTML string
    """
    if not events:
        return _format_empty_digest()

    # Group events by RTO
    events_by_rto: Dict[str, List[TriggerEvent]] = {}
    for event in events:
        rto_key = f"{event.rto_code} - {event.rto_name}"
        if rto_key not in events_by_rto:
            events_by_rto[rto_key] = []
        events_by_rto[rto_key].append(event)

    # Count by score
    high_count = sum(1 for e in events if e.outreach_score == "High")
    medium_count = sum(1 for e in events if e.outreach_score == "Medium")
    low_count = sum(1 for e in events if e.outreach_score == "Low")

    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            .summary {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .rto-section {{
                margin: 30px 0;
                border-left: 4px solid #3498db;
                padding-left: 20px;
            }}
            .rto-name {{
                font-size: 1.3em;
                color: #2c3e50;
                margin-bottom: 15px;
            }}
            .event {{
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin: 15px 0;
            }}
            .event-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .event-type {{
                font-weight: 600;
                color: #555;
            }}
            .score-badge {{
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 600;
            }}
            .score-high {{
                background: #e74c3c;
                color: white;
            }}
            .score-medium {{
                background: #f39c12;
                color: white;
            }}
            .score-low {{
                background: #95a5a6;
                color: white;
            }}
            .suggested-opening {{
                background: #ebf5fb;
                padding: 12px;
                border-radius: 5px;
                margin: 10px 0;
                font-style: italic;
            }}
            .implication {{
                color: #555;
                margin: 10px 0;
            }}
            .source-link {{
                color: #3498db;
                text-decoration: none;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <h1>🎯 RTO Intel Daily Digest</h1>
        <p><strong>{datetime.now().strftime('%A, %B %d, %Y')}</strong></p>

        <div class="summary">
            <strong>Today's Summary:</strong><br>
            {high_count} High priority • {medium_count} Medium priority • {low_count} Low priority<br>
            Across {len(events_by_rto)} RTOs
        </div>
    """

    # Sort RTOs by highest priority event
    def rto_priority(rto_events):
        if any(e.outreach_score == "High" for e in rto_events[1]):
            return 0
        if any(e.outreach_score == "Medium" for e in rto_events[1]):
            return 1
        return 2

    sorted_rtos = sorted(events_by_rto.items(), key=rto_priority)

    # Add each RTO section
    for rto_key, rto_events in sorted_rtos:
        html += f"""
        <div class="rto-section">
            <div class="rto-name">{rto_key}</div>
        """

        # Sort events by score
        score_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_events = sorted(
            rto_events, key=lambda e: score_order.get(e.outreach_score, 3)
        )

        for event in sorted_events:
            score_class = f"score-{event.outreach_score.lower()}"
            html += f"""
            <div class="event">
                <div class="event-header">
                    <span class="event-type">{event.event_category} - {event.event_type.replace('_', ' ').title()}</span>
                    <span class="score-badge {score_class}">{event.outreach_score}</span>
                </div>

                {f'<div class="suggested-opening"><strong>Opening:</strong> {event.suggested_opening}</div>' if event.suggested_opening else ''}

                {f'<div class="implication"><strong>Implication:</strong> {event.business_implication}</div>' if event.business_implication else ''}

                {f'<a href="{event.source_url}" class="source-link">View on training.gov.au →</a>' if event.source_url else ''}
            </div>
            """

        html += "</div>"

    html += """
    </body>
    </html>
    """

    return html


def _format_empty_digest() -> str:
    """Format digest when no events detected."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .empty-state {{
                background: #f8f9fa;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>🎯 RTO Intel Daily Digest</h1>
        <p><strong>{datetime.now().strftime('%A, %B %d, %Y')}</strong></p>

        <div class="empty-state">
            <h2>No Changes Detected</h2>
            <p>All monitored RTOs remain unchanged since the last check.</p>
            <p>The pipeline is running normally.</p>
        </div>
    </body>
    </html>
    """
