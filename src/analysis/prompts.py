"""Prompt templates for Claude AI outreach analysis."""

SYSTEM_PROMPT = """You are an expert sales intelligence analyst helping Jimmy, an AI consulting business owner who sells to Australian Registered Training Organisations (RTOs).

Your role is to analyze changes detected at RTOs and assess their relevance for sales outreach.

Jimmy's consulting offerings:
- AI-powered compliance documentation tools
- Automated training resource development
- Workflow automation for RTO operations
- AI assistants for student support and admin tasks

Outreach Scoring Rubric:
- HIGH: Direct trigger for immediate outreach (regulatory pressure, scope expansion, strategic shifts)
- MEDIUM: Relevant but not urgent (minor scope changes, contact updates)
- LOW: Informational only (minor data corrections, routine updates)

For each event, provide:
1. outreach_score: "High", "Medium", or "Low"
2. suggested_opening: 1-2 sentences demonstrating awareness of the change
3. business_implication: 1-2 sentences explaining the compliance/operational impact

Be specific and contextual. Avoid generic phrases. Reference the actual change details."""


def build_analysis_prompt(
    rto_context: dict,
    events: list,
) -> str:
    """Build prompt for analyzing RTO events.

    Args:
        rto_context: Dict with RTO details (name, code, industry, etc.)
        events: List of TriggerEvent dicts

    Returns:
        Formatted prompt string
    """
    # Format RTO context
    rto_name = rto_context.get("name", "Unknown RTO")
    rto_code = rto_context.get("rto_code", "")
    industry = rto_context.get("industry", "Unknown")
    qual_count = rto_context.get("qual_count", 0)

    # Format events for prompt
    events_text = []
    for i, event in enumerate(events, 1):
        event_type = event.get("event_type", "unknown")
        event_category = event.get("event_category", "unknown")
        new_value = event.get("new_value", "")
        old_value = event.get("old_value", "")

        # Truncate large JSON for readability
        if new_value and len(new_value) > 500:
            new_value = new_value[:500] + "... [truncated]"
        if old_value and len(old_value) > 500:
            old_value = old_value[:500] + "... [truncated]"

        events_text.append(
            f"Event {i}:\n"
            f"  Type: {event_type}\n"
            f"  Category: {event_category}\n"
            f"  Previous: {old_value or 'N/A'}\n"
            f"  Current: {new_value}\n"
        )

    prompt = f"""Analyze these changes detected at an Australian RTO:

RTO Details:
- Name: {rto_name}
- Code: {rto_code}
- Industry Focus: {industry}
- Qualifications on Scope: {qual_count}

Changes Detected:
{chr(10).join(events_text)}

For each event, provide your analysis in this JSON format:
{{
  "events": [
    {{
      "event_number": 1,
      "outreach_score": "High|Medium|Low",
      "suggested_opening": "...",
      "business_implication": "..."
    }},
    ...
  ]
}}

Return ONLY the JSON object, no additional text."""

    return prompt
