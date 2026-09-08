"""Download/read the UCI Student Performance CSV into the raw layer."""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from src.utils.logging_config import DATA_ROOT, PROJECT_ROOT, configure_logging, ensure_directories

UCI_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip"
LOG_PATH = PROJECT_ROOT / "logs" / "ingestion_log.csv"


def _write_log(source: str, status: str, row_count: int = 0, error: str = "") -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["extracted_at", "source", "status", "row_count", "error"])
        if not exists:
            writer.writeheader()
        writer.writerow({"extracted_at": datetime.now(timezone.utc).isoformat(), "source": source,
                         "status": status, "row_count": row_count, "error": error})


def extract_dataset(url: str = UCI_URL, subject: str = "mat") -> Path | None:
    """Extract one UCI subject file and save an untouched, timestamped raw CSV."""
    logger = configure_logging()
    ensure_directories()
    try:
        with urlopen(url, timeout=30) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        member = f"student-{subject}.csv"
        with archive.open(member) as source:
            frame = pd.read_csv(source, sep=";")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = DATA_ROOT / "raw" / f"student_{subject}_{timestamp}.csv"
        frame.to_csv(output, index=False)
        _write_log(f"{url}::{member}", "success", len(frame))
        logger.info("Extracted %s rows to %s", len(frame), output)
        return output
    except Exception as exc:  # DAG should record failure and let Airflow handle retries.
        _write_log(f"{url}::student-{subject}.csv", "fail", error=str(exc))
        logger.exception("Extraction failed: %s", exc)
        return None


if __name__ == "__main__":
    extract_dataset()
