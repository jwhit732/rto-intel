"""Data models for RTO Intel pipeline."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Prospect:
    """RTO prospect loaded from spreadsheet."""

    rto_code: str
    name: str
    legal_name: str
    status: Optional[str] = None
    abn: Optional[str] = None
    rto_type: Optional[str] = None
    industry: Optional[str] = None
    industry_confidence: Optional[float] = None
    web_url: Optional[str] = None
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    location_area: Optional[str] = None
    qual_count: Optional[int] = None
    qualifications: Optional[str] = None
    prospect_score: Optional[int] = None
    imported_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None


@dataclass
class TriggerEvent:
    """Change event detected during monitoring."""

    rto_code: str
    rto_name: str
    event_type: str  # scope_added, scope_removed, regulatory_new, etc.
    event_category: str  # Scope, Regulatory, Registration, Contact, etc.
    new_value: str  # JSON
    old_value: Optional[str] = None  # JSON
    detected_at: Optional[datetime] = None
    outreach_score: Optional[str] = None  # High, Medium, Low
    suggested_opening: Optional[str] = None
    business_implication: Optional[str] = None
    source_url: Optional[str] = None
    delivery_status: str = "pending"
    outreach_status: str = "New"
    id: Optional[int] = None
