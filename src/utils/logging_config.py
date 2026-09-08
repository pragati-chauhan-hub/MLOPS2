"""Shared logging and path helpers for the student pipeline."""
from __future__ import annotations

import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"


def configure_logging() -> logging.Logger:
    """Return a consistently configured pipeline logger."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("student_pipeline")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def ensure_directories() -> None:
    """Create all runtime directories used by the pipeline."""
    for directory in (DATA_ROOT / name for name in ("raw", "staging", "cleaned", "rejected")):
        directory.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
