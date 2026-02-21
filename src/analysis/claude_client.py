"""Claude API client for outreach analysis."""

import json
import logging
from typing import List

import anthropic

from src.analysis.prompts import SYSTEM_PROMPT, build_analysis_prompt
from src.storage.models import TriggerEvent

logger = logging.getLogger(__name__)


class OutreachAnalyser:
    """Uses Claude API to analyze trigger events for outreach relevance."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def analyse_rto_events(
        self, rto_context: dict, events: List[TriggerEvent]
    ) -> List[TriggerEvent]:
        """Analyze events for an RTO and enrich with AI insights.

        Args:
            rto_context: Dict with RTO details
            events: List of TriggerEvent objects

        Returns:
            Same events enriched with outreach_score, suggested_opening, business_implication
        """
        if not events:
            return events

        logger.info(
            f"Analyzing {len(events)} events for RTO {rto_context.get('rto_code')}"
        )

        # Convert events to dicts for prompt
        events_dicts = [
            {
                "event_type": e.event_type,
                "event_category": e.event_category,
                "old_value": e.old_value,
                "new_value": e.new_value,
            }
            for e in events
        ]

        # Build prompt
        user_prompt = build_analysis_prompt(rto_context, events_dicts)

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract response text
            response_text = response.content[0].text

            # Strip markdown code fences if present
            if response_text.strip().startswith("```"):
                # Remove ```json and ``` wrappers
                lines = response_text.strip().split("\n")
                response_text = "\n".join(lines[1:-1])

            # Parse JSON response
            analysis = json.loads(response_text)

            # Enrich events with analysis
            for i, event in enumerate(events):
                event_analysis = analysis["events"][i]
                event.outreach_score = event_analysis.get("outreach_score", "Low")
                event.suggested_opening = event_analysis.get("suggested_opening", "")
                event.business_implication = event_analysis.get(
                    "business_implication", ""
                )

            logger.info(
                f"Successfully analyzed {len(events)} events for RTO {rto_context.get('rto_code')}"
            )

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse Claude response as JSON: {e}\n"
                f"Response: {response_text[:500]}"
            )
            # Return events un-enriched rather than failing completely
            for event in events:
                event.outreach_score = "Low"
                event.suggested_opening = "Unable to analyze"
                event.business_implication = "Analysis failed"

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            # Return events un-enriched
            for event in events:
                event.outreach_score = "Low"
                event.suggested_opening = "Error during analysis"
                event.business_implication = str(e)

        return events
