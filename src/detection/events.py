"""Trigger event types and categorization."""

from enum import Enum
from typing import Any, Dict


class EventCategory(Enum):
    """High-level event categories."""

    SCOPE = "Scope"
    REGULATORY = "Regulatory"
    REGISTRATION = "Registration"
    CONTACT = "Contact"
    RESTRICTION = "Restriction"
    TRAINING = "Training"
    NEWS = "News"


class EventType(Enum):
    """Specific event types."""

    # Scope events
    SCOPE_ADDED = "scope_added"
    SCOPE_REMOVED = "scope_removed"
    SCOPE_CHANGED = "scope_changed"

    # Regulatory events
    REGULATORY_NEW = "regulatory_new"
    REGULATORY_UPDATED = "regulatory_updated"

    # Registration events
    REGISTRATION_STATUS_CHANGED = "registration_status_changed"
    REGISTRATION_EXPIRY_CHANGED = "registration_expiry_changed"
    REGISTRATION_MANAGER_CHANGED = "registration_manager_changed"

    # Contact events
    CONTACT_ADDED = "contact_added"
    CONTACT_REMOVED = "contact_removed"
    CONTACT_CHANGED = "contact_changed"

    # Restriction events
    RESTRICTION_ADDED = "restriction_added"
    RESTRICTION_REMOVED = "restriction_removed"

    # Training package events
    TRAINING_PACKAGE_SUPERSEDED = "training_package_superseded"
    TRAINING_PACKAGE_UPDATED = "training_package_updated"

    # External news
    INDUSTRY_NEWS = "industry_news"


# Event type to category mapping
EVENT_CATEGORY_MAP = {
    EventType.SCOPE_ADDED: EventCategory.SCOPE,
    EventType.SCOPE_REMOVED: EventCategory.SCOPE,
    EventType.SCOPE_CHANGED: EventCategory.SCOPE,
    EventType.REGULATORY_NEW: EventCategory.REGULATORY,
    EventType.REGULATORY_UPDATED: EventCategory.REGULATORY,
    EventType.REGISTRATION_STATUS_CHANGED: EventCategory.REGISTRATION,
    EventType.REGISTRATION_EXPIRY_CHANGED: EventCategory.REGISTRATION,
    EventType.REGISTRATION_MANAGER_CHANGED: EventCategory.REGISTRATION,
    EventType.CONTACT_ADDED: EventCategory.CONTACT,
    EventType.CONTACT_REMOVED: EventCategory.CONTACT,
    EventType.CONTACT_CHANGED: EventCategory.CONTACT,
    EventType.RESTRICTION_ADDED: EventCategory.RESTRICTION,
    EventType.RESTRICTION_REMOVED: EventCategory.RESTRICTION,
    EventType.TRAINING_PACKAGE_SUPERSEDED: EventCategory.TRAINING,
    EventType.TRAINING_PACKAGE_UPDATED: EventCategory.TRAINING,
    EventType.INDUSTRY_NEWS: EventCategory.NEWS,
}


def get_event_category(event_type: EventType) -> EventCategory:
    """Get category for an event type."""
    return EVENT_CATEGORY_MAP.get(event_type, EventCategory.SCOPE)


def make_source_url(rto_code: str, endpoint: str) -> str:
    """Generate training.gov.au source URL for an event."""
    base = f"https://training.gov.au/organisation/details/{rto_code}"

    endpoint_map = {
        "scope": f"{base}#scope",
        "regulatory": f"{base}#regulatory",
        "registration": f"{base}#registration",
        "contacts": f"{base}#contacts",
        "restrictions": f"{base}#restrictions",
    }

    return endpoint_map.get(endpoint, base)
