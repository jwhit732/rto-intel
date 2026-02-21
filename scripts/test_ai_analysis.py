"""Test AI analysis with simulated RTO changes."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.claude_client import OutreachAnalyser
from src.config import config
from src.delivery.digest import format_digest
from src.detection.events import EventType, EventCategory
from src.storage.database import Database
from src.storage.models import TriggerEvent

print("=" * 70)
print("AI Analysis Test - Simulated RTO Changes")
print("=" * 70)

# Get a real prospect from database for context
db = Database(config.database_path)
db.connect()

prospect_codes = db.get_all_prospect_codes()[:3]
print(f"\nTesting with {len(prospect_codes)} RTOs: {prospect_codes}\n")

# Simulate realistic RTO changes
test_scenarios = [
    {
        "rto_code": prospect_codes[0],
        "scenario": "Scope Expansion - New Qualifications",
        "events": [
            TriggerEvent(
                rto_code=prospect_codes[0],
                rto_name="Servitium Group Pty Ltd",
                event_type=EventType.SCOPE_ADDED.value,
                event_category=EventCategory.SCOPE.value,
                old_value=None,
                new_value=json.dumps({
                    "code": "BSB50120",
                    "title": "Diploma of Business",
                    "status": "Current",
                    "added_date": "2026-02-15"
                }),
                source_url=f"https://training.gov.au/organisation/details/{prospect_codes[0]}#scope",
            ),
            TriggerEvent(
                rto_code=prospect_codes[0],
                rto_name="Servitium Group Pty Ltd",
                event_type=EventType.SCOPE_ADDED.value,
                event_category=EventCategory.SCOPE.value,
                old_value=None,
                new_value=json.dumps({
                    "code": "BSB60120",
                    "title": "Advanced Diploma of Business",
                    "status": "Current",
                    "added_date": "2026-02-15"
                }),
                source_url=f"https://training.gov.au/organisation/details/{prospect_codes[0]}#scope",
            ),
        ]
    },
    {
        "rto_code": prospect_codes[1],
        "scenario": "Regulatory Decision - Audit Outcome",
        "events": [
            TriggerEvent(
                rto_code=prospect_codes[1],
                rto_name="Austral College",
                event_type=EventType.REGULATORY_NEW.value,
                event_category=EventCategory.REGULATORY.value,
                old_value=None,
                new_value=json.dumps({
                    "decision_type": "Audit",
                    "outcome": "Compliant with conditions",
                    "conditions": [
                        "Must improve assessment validation processes within 90 days",
                        "Submit monthly compliance reports for 6 months"
                    ],
                    "decision_date": "2026-02-10",
                    "effective_date": "2026-02-15"
                }),
                source_url=f"https://training.gov.au/organisation/details/{prospect_codes[1]}#regulatory",
            ),
        ]
    },
    {
        "rto_code": prospect_codes[2],
        "scenario": "Scope Removal - Qualifications Dropped",
        "events": [
            TriggerEvent(
                rto_code=prospect_codes[2],
                rto_name="Landscape Skills",
                event_type=EventType.SCOPE_REMOVED.value,
                event_category=EventCategory.SCOPE.value,
                old_value=json.dumps({
                    "code": "AHC30716",
                    "title": "Certificate III in Horticulture",
                    "status": "Superseded"
                }),
                new_value=None,
                source_url=f"https://training.gov.au/organisation/details/{prospect_codes[2]}#scope",
            ),
        ]
    }
]

# Analyze each scenario with Claude
analyser = OutreachAnalyser(
    api_key=config.anthropic_api_key,
    model=config.anthropic_model
)

all_enriched_events = []

for scenario in test_scenarios:
    print(f"\n{'='*70}")
    print(f"Scenario: {scenario['scenario']}")
    print(f"RTO: {scenario['rto_code']}")
    print(f"Events: {len(scenario['events'])}")
    print(f"{'='*70}\n")

    # Get prospect context
    prospect = db.get_prospect(scenario['rto_code'])
    rto_context = {
        "rto_code": scenario['rto_code'],
        "name": prospect.name if prospect else "Unknown",
        "industry": prospect.industry if prospect else "Unknown",
        "qual_count": prospect.qual_count if prospect else 0,
    }

    print(f"RTO Context:")
    print(f"  Name: {rto_context['name']}")
    print(f"  Industry: {rto_context['industry']}")
    print(f"  Qualifications on scope: {rto_context['qual_count']}")

    # Analyze with Claude
    print(f"\nAnalyzing with Claude Sonnet 4.6...")
    enriched_events = analyser.analyse_rto_events(rto_context, scenario['events'])

    # Display results
    for i, event in enumerate(enriched_events, 1):
        print(f"\n  Event {i}:")
        print(f"    Type: {event.event_type}")
        print(f"    Score: {event.outreach_score}")
        print(f"    Opening: \"{event.suggested_opening}\"")
        print(f"    Implication: \"{event.business_implication}\"")

    all_enriched_events.extend(enriched_events)

db.close()

# Generate HTML digest
print(f"\n{'='*70}")
print("Generating HTML Digest")
print(f"{'='*70}\n")

html_digest = format_digest(all_enriched_events)

# Save digest
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

digest_file = output_dir / f"ai_test_digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
digest_file.write_text(html_digest, encoding="utf-8")

print(f"Digest saved: {digest_file}")

# Summary
high = sum(1 for e in all_enriched_events if e.outreach_score == "High")
medium = sum(1 for e in all_enriched_events if e.outreach_score == "Medium")
low = sum(1 for e in all_enriched_events if e.outreach_score == "Low")

print(f"\n{'='*70}")
print("Summary")
print(f"{'='*70}")
print(f"Total events analyzed: {len(all_enriched_events)}")
print(f"Priority breakdown: {high} High, {medium} Medium, {low} Low")
print(f"\nOpen the digest file in your browser to see the formatted output!")
print(f"{'='*70}\n")
