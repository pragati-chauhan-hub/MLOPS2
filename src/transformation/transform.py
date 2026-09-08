"""Build the analytical student-performance dataset."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.utils.logging_config import DATA_ROOT, ensure_directories


def transform_dataset(input_path: str | Path) -> Path:
    """Create student-level features from validated UCI records.

    The UCI source has no attendance or assignment columns. Absence-based attendance
    and a study-time/failure proxy are documented in docs/data_dictionary.md.
    """
    ensure_directories()
    frame = pd.read_csv(input_path)
    frame["subject"] = frame.get("subject", "mathematics")
    frame["semester"] = "current"
    frame["department"] = "general"
    frame["attendance_percentage"] = (100 * (1 - frame["absences"].clip(lower=0, upper=93) / 93)).round(2)
    frame["average_internal_marks"] = frame[["G1", "G2"]].mean(axis=1).round(2)
    frame["previous_grade"] = frame["G1"]
    frame["assignment_completion_rate"] = (
        100 * (frame["studytime"].clip(lower=1, upper=4) / 4) * (1 - frame["failures"].clip(lower=0, upper=3) / 4)
    ).clip(0, 100).round(2)
    frame["pass_flag"] = (frame["G3"] >= 10).astype(int)
    frame["risk_flag"] = (
        (frame["G3"] < 10) | (frame["attendance_percentage"] < 80) | (frame["failures"] > 0)
    ).astype(int)
    frame["risk_reason"] = frame.apply(
        lambda row: "; ".join(
            reason for reason, condition in (
                ("final_mark_below_10", row["G3"] < 10),
                ("attendance_below_80_percent", row["attendance_percentage"] < 80),
                ("prior_failures", row["failures"] > 0),
            ) if condition
        ) or "no_rule_triggered",
        axis=1,
    )
    frame["processed_at"] = datetime.now(timezone.utc).isoformat()
    output = DATA_ROOT / "cleaned" / f"student_performance_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    frame.to_csv(output, index=False)
    return output


def latest_cleaned() -> Path:
    files = sorted((DATA_ROOT / "cleaned").glob("student_performance_*.csv"))
    if not files:
        raise FileNotFoundError("No cleaned dataset found")
    return files[-1]
