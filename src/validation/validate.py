"""Rule-based validation and cleaning for the UCI student dataset."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils.logging_config import DATA_ROOT, ensure_directories

MARK_COLUMNS = ["G1", "G2", "G3"]
REQUIRED_COLUMNS = {"school", "sex", "age", "G1", "G2", "G3"}


def _student_id(frame: pd.DataFrame) -> pd.Series:
    """Create a stable ID from source identity fields, with a row fallback."""
    identity = frame.astype(str)
    return identity.astype(str).agg("|".join, axis=1).map(
        lambda value: f"S{hashlib.sha256(value.encode('utf-8')).hexdigest()[:10].upper()}"
    )


def validate_dataset(input_path: str | Path) -> Path:
    """Clean valid rows, and write all rejected rows with an explicit reason."""
    ensure_directories()
    frame = pd.read_csv(input_path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame.insert(0, "student_id", _student_id(frame))
    frame["source_file"] = Path(input_path).name
    frame["validation_status"] = "valid"

    rejected_parts: list[pd.DataFrame] = []
    duplicate_mask = frame.duplicated(keep="first")
    if duplicate_mask.any():
        rejected = frame.loc[duplicate_mask].copy()
        rejected["reason"] = "duplicate_record"
        rejected_parts.append(rejected)
    valid = frame.loc[~duplicate_mask].copy()

    marks_numeric = valid[MARK_COLUMNS].apply(pd.to_numeric, errors="coerce")
    invalid_marks = marks_numeric.isna().any(axis=1) | (marks_numeric.lt(0) | marks_numeric.gt(20)).any(axis=1)
    if invalid_marks.any():
        rejected = valid.loc[invalid_marks].copy()
        rejected["reason"] = "mark_out_of_range_or_non_numeric"
        rejected_parts.append(rejected)
    valid = valid.loc[~invalid_marks].copy()
    valid[MARK_COLUMNS] = marks_numeric.loc[valid.index]

    rejected_path = DATA_ROOT / "rejected" / f"rejected_records_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    if rejected_parts:
        pd.concat(rejected_parts, ignore_index=True).to_csv(rejected_path, index=False)
    else:
        pd.DataFrame(columns=[*frame.columns, "reason"]).to_csv(rejected_path, index=False)

    output = DATA_ROOT / "staging" / f"validated_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    valid.to_csv(output, index=False)
    return output


def latest_validated() -> Path:
    files = sorted((DATA_ROOT / "staging").glob("validated_*.csv"))
    if not files:
        raise FileNotFoundError("No validated dataset found")
    return files[-1]
