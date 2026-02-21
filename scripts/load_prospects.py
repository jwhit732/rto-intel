"""Load prospect data from Excel into SQLite database."""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.storage.database import Database
from src.storage.models import Prospect

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_prospects():
    """Load top N prospects from Excel into database."""
    logger.info(f"Loading prospects from {config.prospects_file}")

    # Read Excel file
    try:
        df = pd.read_excel(config.prospects_file)
    except FileNotFoundError:
        logger.error(f"Prospects file not found: {config.prospects_file}")
        return
    except Exception as e:
        logger.error(f"Error reading Excel file: {e}")
        return

    logger.info(f"Read {len(df)} rows from spreadsheet")

    # Sort by prospect_score descending and take top N
    df_sorted = df.sort_values("prospect_score", ascending=False)
    df_top = df_sorted.head(config.top_n_prospects)

    logger.info(
        f"Selected top {len(df_top)} prospects "
        f"(score range: {df_top['prospect_score'].min()}-{df_top['prospect_score'].max()})"
    )

    # Convert to Prospect objects
    prospects = []
    for _, row in df_top.iterrows():
        # Convert code to string
        rto_code = str(row["code"]) if pd.notna(row["code"]) else None
        if not rto_code:
            logger.warning(f"Skipping row with missing RTO code: {row.get('name')}")
            continue

        prospect = Prospect(
            rto_code=rto_code,
            name=row.get("name", ""),
            legal_name=row.get("legal_name", ""),
            status=row.get("status") if pd.notna(row.get("status")) else None,
            abn=str(row.get("abn")) if pd.notna(row.get("abn")) else None,
            industry=row.get("industry") if pd.notna(row.get("industry")) else None,
            industry_confidence=(
                float(row.get("industry_confidence"))
                if pd.notna(row.get("industry_confidence"))
                else None
            ),
            web_url=(
                row.get("training_gov_url")
                if pd.notna(row.get("training_gov_url"))
                else None
            ),
            website=row.get("website") if pd.notna(row.get("website")) else None,
            contact_name=(
                row.get("contact_name") if pd.notna(row.get("contact_name")) else None
            ),
            contact_role=(
                row.get("contact_role") if pd.notna(row.get("contact_role")) else None
            ),
            contact_email=(
                row.get("contact_email")
                if pd.notna(row.get("contact_email"))
                else None
            ),
            contact_phone=(
                row.get("contact_phone")
                if pd.notna(row.get("contact_phone"))
                else None
            ),
            location_area=(
                row.get("location_area")
                if pd.notna(row.get("location_area"))
                else None
            ),
            qual_count=(
                int(row.get("qual_count"))
                if pd.notna(row.get("qual_count"))
                else None
            ),
            qualifications=(
                row.get("qualifications")
                if pd.notna(row.get("qualifications"))
                else None
            ),
            prospect_score=(
                int(row.get("prospect_score"))
                if pd.notna(row.get("prospect_score"))
                else None
            ),
        )
        prospects.append(prospect)

    logger.info(f"Converted {len(prospects)} rows to Prospect objects")

    # Insert into database
    with Database(config.database_path) as db:
        db.init_schema()

        for prospect in prospects:
            try:
                db.insert_prospect(prospect)
            except Exception as e:
                logger.error(f"Error inserting RTO {prospect.rto_code}: {e}")
                continue

        logger.info(f"Successfully loaded {len(prospects)} prospects into database")

        # Show summary
        all_codes = db.get_all_prospect_codes()
        logger.info(f"Total prospects in database: {len(all_codes)}")
        logger.info(f"First 5 RTO codes: {all_codes[:5]}")


if __name__ == "__main__":
    load_prospects()
