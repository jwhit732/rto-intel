"""Configuration loader and validator for RTO Intel pipeline."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Configuration container loaded from environment variables."""

    def __init__(self):
        """Load configuration from .env file and environment."""
        # Load .env file from project root
        load_dotenv()

        # Anthropic API
        self.anthropic_api_key: str = self._require("ANTHROPIC_API_KEY")
        self.anthropic_model: str = os.getenv(
            "ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"
        )

        # training.gov.au API
        self.tga_api_base_url: str = os.getenv(
            "TGA_API_BASE_URL", "https://training.gov.au/api"
        )
        self.tga_rate_limit_seconds: float = float(
            os.getenv("TGA_RATE_LIMIT_SECONDS", "1.5")
        )

        # Make.com webhooks (optional for testing)
        self.make_webhook_digest: Optional[str] = os.getenv("MAKE_WEBHOOK_DIGEST")
        self.make_webhook_sheets: Optional[str] = os.getenv("MAKE_WEBHOOK_SHEETS")

        # File paths
        self.prospects_file: Path = Path(
            os.getenv("PROSPECTS_FILE", "prospects/asqa_rtos_scored.xlsx")
        )
        self.database_path: Path = Path(
            os.getenv("DATABASE_PATH", "data/rto_intel.db")
        )

        # Pipeline config
        self.top_n_prospects: int = int(os.getenv("TOP_N_PROSPECTS", "350"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.daily_budget_alert_usd: float = float(
            os.getenv("DAILY_BUDGET_ALERT_USD", "5.00")
        )

        # Validate critical paths exist
        self._validate()

    def _require(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable {key} is not set. "
                f"Copy .env.example to .env and configure."
            )
        return value

    def _validate(self):
        """Validate configuration."""
        # Prospects file is optional (only needed for initial load)
        # Weekly runs read from database, not Excel

        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
