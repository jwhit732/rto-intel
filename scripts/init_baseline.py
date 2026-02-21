"""Initialize baseline snapshots for all prospects."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.tga_client import TGAClient
from src.config import config
from src.storage.database import Database

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def fetch_and_store_baseline(
    db: Database, client: TGAClient, rto_code: str, index: int, total: int
):
    """Fetch and store baseline for a single RTO.

    Args:
        db: Database connection
        client: TGA API client
        rto_code: RTO code
        index: Current index (for progress)
        total: Total count (for progress)
    """
    logger.info(f"[{index}/{total}] Fetching baseline for RTO {rto_code}")

    try:
        # Fetch all endpoints
        data = await client.get_full_rto_data(rto_code)

        # Store each endpoint as a baseline
        endpoints_stored = 0
        for endpoint, response in data.items():
            if response is not None:
                db.store_baseline(rto_code, endpoint, response)
                endpoints_stored += 1

        # Update last_checked timestamp
        db.update_prospect_last_checked(rto_code)

        logger.info(
            f"[{index}/{total}] RTO {rto_code}: Stored {endpoints_stored}/6 endpoints"
        )
        return True

    except Exception as e:
        logger.error(f"[{index}/{total}] RTO {rto_code}: Error: {e}")
        return False


async def init_all_baselines():
    """Initialize baselines for all prospects."""
    logger.info("Starting baseline initialization")

    # Open database connection
    db = Database(config.database_path)
    db.connect()
    db.init_schema()

    # Get all prospect codes
    prospect_codes = db.get_all_prospect_codes()
    total = len(prospect_codes)

    if total == 0:
        logger.error(
            "No prospects found in database. Run load_prospects.py first."
        )
        return

    logger.info(f"Found {total} prospects to fetch")

    # Create TGA client
    client = TGAClient(
        base_url=config.tga_api_base_url,
        rate_limit_seconds=config.tga_rate_limit_seconds,
    )

    # Fetch baselines for all prospects
    success_count = 0
    error_count = 0

    for index, rto_code in enumerate(prospect_codes, start=1):
        success = await fetch_and_store_baseline(db, client, rto_code, index, total)
        if success:
            success_count += 1
        else:
            error_count += 1

    # Close database
    db.close()

    # Summary
    logger.info("=" * 60)
    logger.info("Baseline initialization complete")
    logger.info(f"Total prospects: {total}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_all_baselines())
