"""Change detection engine using deepdiff."""

import json
import logging
from typing import Any, Dict, List, Optional

from deepdiff import DeepDiff

from src.detection.events import (
    EventType,
    get_event_category,
    make_source_url,
)
from src.storage.models import TriggerEvent

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detects changes between current and baseline API data."""

    def detect_all_changes(
        self,
        rto_code: str,
        rto_name: str,
        current_data: Dict[str, Optional[Dict]],
        baseline_data: Dict[str, Optional[Dict]],
    ) -> List[TriggerEvent]:
        """Detect all changes across all endpoints.

        Args:
            rto_code: RTO code
            rto_name: RTO name
            current_data: Current API responses by endpoint
            baseline_data: Baseline API responses by endpoint

        Returns:
            List of detected trigger events
        """
        events = []

        # Check each endpoint
        for endpoint in ["scope", "regulatory", "registration", "contacts", "restrictions"]:
            current = current_data.get(endpoint)
            baseline = baseline_data.get(endpoint)

            # Skip if both are None
            if current is None and baseline is None:
                continue

            # Detect changes for this endpoint
            endpoint_events = self._detect_endpoint_changes(
                rto_code, rto_name, endpoint, current, baseline
            )
            events.extend(endpoint_events)

        return events

    def _detect_endpoint_changes(
        self,
        rto_code: str,
        rto_name: str,
        endpoint: str,
        current: Optional[Dict],
        baseline: Optional[Dict],
    ) -> List[TriggerEvent]:
        """Detect changes for a specific endpoint."""
        # New data appeared where there was none
        if baseline is None and current is not None:
            return self._handle_new_data(rto_code, rto_name, endpoint, current)

        # Data disappeared
        if baseline is not None and current is None:
            return self._handle_removed_data(rto_code, rto_name, endpoint, baseline)

        # Both exist - compare
        if baseline is not None and current is not None:
            return self._compare_data(
                rto_code, rto_name, endpoint, current, baseline
            )

        return []

    def _handle_new_data(
        self, rto_code: str, rto_name: str, endpoint: str, data: Dict
    ) -> List[TriggerEvent]:
        """Handle case where new data appeared."""
        logger.info(f"RTO {rto_code}: New {endpoint} data appeared")

        event_type = EventType.SCOPE_ADDED
        if endpoint == "regulatory":
            event_type = EventType.REGULATORY_NEW
        elif endpoint == "restrictions":
            event_type = EventType.RESTRICTION_ADDED

        return [
            TriggerEvent(
                rto_code=rto_code,
                rto_name=rto_name,
                event_type=event_type.value,
                event_category=get_event_category(event_type).value,
                old_value=None,
                new_value=json.dumps(data),
                source_url=make_source_url(rto_code, endpoint),
            )
        ]

    def _handle_removed_data(
        self, rto_code: str, rto_name: str, endpoint: str, data: Dict
    ) -> List[TriggerEvent]:
        """Handle case where data was removed."""
        logger.info(f"RTO {rto_code}: {endpoint} data was removed")

        event_type = EventType.SCOPE_REMOVED
        if endpoint == "regulatory":
            event_type = EventType.REGULATORY_UPDATED
        elif endpoint == "restrictions":
            event_type = EventType.RESTRICTION_REMOVED

        return [
            TriggerEvent(
                rto_code=rto_code,
                rto_name=rto_name,
                event_type=event_type.value,
                event_category=get_event_category(event_type).value,
                old_value=json.dumps(data),
                new_value=None,
                source_url=make_source_url(rto_code, endpoint),
            )
        ]

    def _compare_data(
        self,
        rto_code: str,
        rto_name: str,
        endpoint: str,
        current: Dict,
        baseline: Dict,
    ) -> List[TriggerEvent]:
        """Compare current and baseline data for changes."""
        # Use deepdiff for structural comparison
        diff = DeepDiff(baseline, current, ignore_order=True)

        if not diff:
            # No changes detected
            return []

        logger.info(f"RTO {rto_code}: Changes detected in {endpoint}")

        # Route to endpoint-specific handlers
        if endpoint == "scope":
            return self._detect_scope_changes(rto_code, rto_name, current, baseline, diff)
        elif endpoint == "regulatory":
            return self._detect_regulatory_changes(rto_code, rto_name, current, baseline, diff)
        elif endpoint == "registration":
            return self._detect_registration_changes(rto_code, rto_name, current, baseline, diff)
        else:
            # Generic change event for other endpoints
            return [
                TriggerEvent(
                    rto_code=rto_code,
                    rto_name=rto_name,
                    event_type=EventType.SCOPE_CHANGED.value,
                    event_category=get_event_category(EventType.SCOPE_CHANGED).value,
                    old_value=json.dumps(baseline),
                    new_value=json.dumps(current),
                    source_url=make_source_url(rto_code, endpoint),
                )
            ]

    def _detect_scope_changes(
        self,
        rto_code: str,
        rto_name: str,
        current: Dict,
        baseline: Dict,
        diff: DeepDiff,
    ) -> List[TriggerEvent]:
        """Detect scope-specific changes (qualifications/units added or removed)."""
        events = []

        # Check for items added
        if "iterable_item_added" in diff:
            for path, value in diff["iterable_item_added"].items():
                events.append(
                    TriggerEvent(
                        rto_code=rto_code,
                        rto_name=rto_name,
                        event_type=EventType.SCOPE_ADDED.value,
                        event_category=EventCategory.SCOPE.value,
                        old_value=None,
                        new_value=json.dumps(value),
                        source_url=make_source_url(rto_code, "scope"),
                    )
                )

        # Check for items removed
        if "iterable_item_removed" in diff:
            for path, value in diff["iterable_item_removed"].items():
                events.append(
                    TriggerEvent(
                        rto_code=rto_code,
                        rto_name=rto_name,
                        event_type=EventType.SCOPE_REMOVED.value,
                        event_category=EventCategory.SCOPE.value,
                        old_value=json.dumps(value),
                        new_value=None,
                        source_url=make_source_url(rto_code, "scope"),
                    )
                )

        # Check for values changed
        if "values_changed" in diff:
            for path, change in diff["values_changed"].items():
                events.append(
                    TriggerEvent(
                        rto_code=rto_code,
                        rto_name=rto_name,
                        event_type=EventType.SCOPE_CHANGED.value,
                        event_category=EventCategory.SCOPE.value,
                        old_value=json.dumps(change.get("old_value")),
                        new_value=json.dumps(change.get("new_value")),
                        source_url=make_source_url(rto_code, "scope"),
                    )
                )

        return events

    def _detect_regulatory_changes(
        self,
        rto_code: str,
        rto_name: str,
        current: Dict,
        baseline: Dict,
        diff: DeepDiff,
    ) -> List[TriggerEvent]:
        """Detect regulatory decision changes."""
        # For regulatory, we mainly care about new decisions
        return [
            TriggerEvent(
                rto_code=rto_code,
                rto_name=rto_name,
                event_type=EventType.REGULATORY_NEW.value,
                event_category=EventCategory.REGULATORY.value,
                old_value=json.dumps(baseline),
                new_value=json.dumps(current),
                source_url=make_source_url(rto_code, "regulatory"),
            )
        ]

    def _detect_registration_changes(
        self,
        rto_code: str,
        rto_name: str,
        current: Dict,
        baseline: Dict,
        diff: DeepDiff,
    ) -> List[TriggerEvent]:
        """Detect registration-related changes."""
        events = []

        # Check for specific field changes
        if "values_changed" in diff:
            for path, change in diff["values_changed"].items():
                # Determine event type based on field
                if "status" in path.lower():
                    event_type = EventType.REGISTRATION_STATUS_CHANGED
                elif "expiry" in path.lower() or "end" in path.lower():
                    event_type = EventType.REGISTRATION_EXPIRY_CHANGED
                else:
                    event_type = EventType.REGISTRATION_STATUS_CHANGED

                events.append(
                    TriggerEvent(
                        rto_code=rto_code,
                        rto_name=rto_name,
                        event_type=event_type.value,
                        event_category=EventCategory.REGISTRATION.value,
                        old_value=json.dumps(change.get("old_value")),
                        new_value=json.dumps(change.get("new_value")),
                        source_url=make_source_url(rto_code, "registration"),
                    )
                )

        return events
