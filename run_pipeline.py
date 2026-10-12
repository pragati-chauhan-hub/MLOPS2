"""
Local pipeline runner: extract → validate → transform → load.

Usage:
    python run_pipeline.py          # full run (downloads fresh data)
    python run_pipeline.py --help
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.extract import extract_dataset
from src.loading.load_to_postgres import database_url, load_dataset
from src.transformation.transform import transform_dataset
from src.utils.logging_config import configure_logging
from src.validation.validate import validate_dataset


def main(subject: str = "mat") -> None:
    logger = configure_logging()

    logger.info("=" * 60)
    logger.info("Student Performance Pipeline  (DB: %s)", database_url())
    logger.info("=" * 60)

    # 1. Extract
    logger.info("[1/4] Extracting UCI dataset (subject=%s)…", subject)
    raw_path = extract_dataset(subject=subject)
    if raw_path is None:
        logger.error("Extraction failed — check logs/ingestion_log.csv")
        sys.exit(1)
    logger.info("      Raw file: %s", raw_path)

    # 2. Validate
    logger.info("[2/4] Validating…")
    validated_path = validate_dataset(raw_path)
    logger.info("      Validated file: %s", validated_path)

    # 3. Transform
    logger.info("[3/4] Transforming…")
    cleaned_path = transform_dataset(validated_path)
    logger.info("      Cleaned file: %s", cleaned_path)

    # 4. Load
    logger.info("[4/4] Loading into database…")
    load_dataset(cleaned_path)
    logger.info("      Done! Database: %s", database_url())

    logger.info("=" * 60)
    logger.info("Pipeline complete. Run the dashboard with:")
    logger.info("  streamlit run dashboard/app.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Student Performance ETL pipeline")
    parser.add_argument("--subject", default="mat", choices=["mat", "por"],
                        help="UCI subject file: mat=Mathematics, por=Portuguese (default: mat)")
    args = parser.parse_args()
    main(subject=args.subject)
