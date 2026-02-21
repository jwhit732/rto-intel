"""SQLite database management for RTO Intel pipeline."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from src.storage.models import Prospect, TriggerEvent


class Database:
    """SQLite database interface for RTO Intel."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Open database connection."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        return self

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def init_schema(self):
        """Create database schema if not exists."""
        cursor = self.conn.cursor()

        # Prospects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prospects (
                rto_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                legal_name TEXT,
                status TEXT,
                abn TEXT,
                rto_type TEXT,
                industry TEXT,
                industry_confidence REAL,
                web_url TEXT,
                website TEXT,
                contact_name TEXT,
                contact_role TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                location_area TEXT,
                qual_count INTEGER,
                qualifications TEXT,
                prospect_score INTEGER,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_checked DATETIME
            )
        """)

        # Baselines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rto_code TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                data_json TEXT NOT NULL,
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(rto_code, endpoint),
                FOREIGN KEY (rto_code) REFERENCES prospects(rto_code)
            )
        """)

        # Trigger events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trigger_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                rto_code TEXT NOT NULL,
                rto_name TEXT,
                event_type TEXT NOT NULL,
                event_category TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                outreach_score TEXT,
                suggested_opening TEXT,
                business_implication TEXT,
                source_url TEXT,
                delivery_status TEXT DEFAULT 'pending',
                outreach_status TEXT DEFAULT 'New',
                FOREIGN KEY (rto_code) REFERENCES prospects(rto_code)
            )
        """)

        # Training baselines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_baselines (
                component_code TEXT PRIMARY KEY,
                component_type TEXT,
                current_release TEXT,
                status TEXT,
                data_json TEXT,
                checked_at DATETIME,
                rto_codes TEXT
            )
        """)

        # News seen table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_seen (
                url_hash TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                relevant BOOLEAN DEFAULT FALSE,
                included_in_digest BOOLEAN DEFAULT FALSE
            )
        """)

        # RTO history table (for pattern memory over time)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rto_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rto_code TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                qual_count INTEGER,
                has_restrictions BOOLEAN,
                scope_items INTEGER,
                regulatory_events INTEGER,
                registration_status TEXT,
                UNIQUE(rto_code, snapshot_date),
                FOREIGN KEY (rto_code) REFERENCES prospects(rto_code)
            )
        """)

        self.conn.commit()

    # Prospect operations
    def insert_prospect(self, prospect: Prospect):
        """Insert a prospect into the database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prospects (
                rto_code, name, legal_name, status, abn, rto_type, industry,
                industry_confidence, web_url, website, contact_name, contact_role,
                contact_email, contact_phone, location_area, qual_count,
                qualifications, prospect_score, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prospect.rto_code, prospect.name, prospect.legal_name, prospect.status,
            prospect.abn, prospect.rto_type, prospect.industry,
            prospect.industry_confidence, prospect.web_url, prospect.website,
            prospect.contact_name, prospect.contact_role, prospect.contact_email,
            prospect.contact_phone, prospect.location_area, prospect.qual_count,
            prospect.qualifications, prospect.prospect_score,
            prospect.imported_at or datetime.now()
        ))
        self.conn.commit()

    def get_all_prospect_codes(self) -> List[str]:
        """Get all RTO codes from prospects table."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT rto_code FROM prospects ORDER BY prospect_score DESC")
        return [row["rto_code"] for row in cursor.fetchall()]

    def get_prospect(self, rto_code: str) -> Optional[Prospect]:
        """Get a prospect by RTO code."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM prospects WHERE rto_code = ?", (rto_code,))
        row = cursor.fetchone()
        if not row:
            return None
        return Prospect(**dict(row))

    # Baseline operations
    def store_baseline(self, rto_code: str, endpoint: str, data: dict):
        """Store baseline snapshot for an RTO endpoint."""
        data_json = json.dumps(data, sort_keys=True)
        data_hash = str(hash(data_json))

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO baselines (
                rto_code, endpoint, data_hash, data_json, captured_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (rto_code, endpoint, data_hash, data_json, datetime.now()))
        self.conn.commit()

    def get_baseline(self, rto_code: str, endpoint: str) -> Optional[dict]:
        """Get baseline snapshot for an RTO endpoint."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT data_json FROM baselines
            WHERE rto_code = ? AND endpoint = ?
        """, (rto_code, endpoint))
        row = cursor.fetchone()
        if not row:
            return None
        return json.loads(row["data_json"])

    def get_baseline_hash(self, rto_code: str, endpoint: str) -> Optional[str]:
        """Get baseline hash for quick comparison."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT data_hash FROM baselines
            WHERE rto_code = ? AND endpoint = ?
        """, (rto_code, endpoint))
        row = cursor.fetchone()
        return row["data_hash"] if row else None

    # Trigger event operations
    def insert_trigger_event(self, event: TriggerEvent) -> int:
        """Insert a trigger event and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trigger_events (
                detected_at, rto_code, rto_name, event_type, event_category,
                old_value, new_value, outreach_score, suggested_opening,
                business_implication, source_url, delivery_status, outreach_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.detected_at or datetime.now(),
            event.rto_code, event.rto_name, event.event_type, event.event_category,
            event.old_value, event.new_value, event.outreach_score,
            event.suggested_opening, event.business_implication, event.source_url,
            event.delivery_status, event.outreach_status
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_pending_events(self) -> List[TriggerEvent]:
        """Get all pending (undelivered) trigger events."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trigger_events
            WHERE delivery_status = 'pending'
            ORDER BY outreach_score DESC, detected_at DESC
        """)
        return [TriggerEvent(**dict(row)) for row in cursor.fetchall()]

    def mark_events_delivered(self, event_ids: List[int]):
        """Mark events as delivered."""
        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(event_ids))
        cursor.execute(f"""
            UPDATE trigger_events
            SET delivery_status = 'delivered'
            WHERE id IN ({placeholders})
        """, event_ids)
        self.conn.commit()

    def update_prospect_last_checked(self, rto_code: str):
        """Update last_checked timestamp for a prospect."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE prospects
            SET last_checked = ?
            WHERE rto_code = ?
        """, (datetime.now(), rto_code))
        self.conn.commit()

    # History operations (for pattern memory)
    def record_rto_snapshot(
        self,
        rto_code: str,
        qual_count: int = 0,
        has_restrictions: bool = False,
        scope_items: int = 0,
        regulatory_events: int = 0,
        registration_status: str = None,
    ):
        """Record weekly snapshot of RTO state for pattern analysis."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO rto_history (
                rto_code, snapshot_date, qual_count, has_restrictions,
                scope_items, regulatory_events, registration_status
            ) VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
        """, (
            rto_code, qual_count, has_restrictions,
            scope_items, regulatory_events, registration_status
        ))
        self.conn.commit()

    def get_rto_trend(self, rto_code: str, weeks: int = 12) -> List[dict]:
        """Get historical snapshots for an RTO."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT snapshot_date, qual_count, has_restrictions,
                   scope_items, regulatory_events, registration_status
            FROM rto_history
            WHERE rto_code = ?
            AND snapshot_date > DATE('now', ?)
            ORDER BY snapshot_date DESC
        """, (rto_code, f'-{weeks} weeks'))
        return [dict(row) for row in cursor.fetchall()]

    def get_expanding_rtos(self, min_scope_changes: int = 3, weeks: int = 12) -> List[str]:
        """Find RTOs showing expansion pattern (growing scope, no restrictions)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT rto_code
            FROM rto_history
            WHERE snapshot_date > DATE('now', ?)
            GROUP BY rto_code
            HAVING SUM(scope_items) > ? AND MAX(has_restrictions) = 0
        """, (f'-{weeks} weeks', min_scope_changes))
        return [row[0] for row in cursor.fetchall()]
