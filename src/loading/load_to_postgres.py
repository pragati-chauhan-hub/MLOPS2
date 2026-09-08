"""Load the analytical dataset into PostgreSQL."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.utils.logging_config import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


def database_url() -> str:
    return (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'student_user')}:{os.getenv('POSTGRES_PASSWORD', 'student_password')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'student_dw')}"
    )


def load_dataset(input_path: str | Path) -> None:
    """Truncate and reload dimensions/fact tables, making each run idempotent."""
    frame = pd.read_csv(input_path)
    engine = create_engine(database_url())
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE fact_student_performance, dim_student, dim_subject, dim_semester, dim_department CASCADE"))
    frame[["student_id", "school", "sex", "age", "address", "famsize", "Pstatus"]].rename(columns={"Pstatus": "pstatus"}).drop_duplicates("student_id").to_sql("dim_student", engine, if_exists="append", index=False)
    pd.DataFrame({"subject": frame["subject"].unique()}).to_sql("dim_subject", engine, if_exists="append", index=False)
    pd.DataFrame({"semester": frame["semester"].unique()}).to_sql("dim_semester", engine, if_exists="append", index=False)
    pd.DataFrame({"department": frame["department"].unique()}).to_sql("dim_department", engine, if_exists="append", index=False)
    fact_columns = ["student_id", "subject", "semester", "department", "G1", "G2", "G3", "attendance_percentage", "average_internal_marks", "assignment_completion_rate", "previous_grade", "pass_flag", "risk_flag", "risk_reason", "absences", "failures"]
    fact_frame = frame[fact_columns].rename(columns={"G1": "g1", "G2": "g2", "G3": "g3"}).copy()
    fact_frame["pass_flag"] = fact_frame["pass_flag"].astype(bool)
    fact_frame["risk_flag"] = fact_frame["risk_flag"].astype(bool)
    fact_frame.to_sql("fact_student_performance", engine, if_exists="append", index=False)
    with engine.begin() as connection:
        connection.execute(text("REFRESH MATERIALIZED VIEW mart_high_risk_students"))
    engine.dispose()


if __name__ == "__main__":
    from src.transformation.transform import latest_cleaned
    load_dataset(latest_cleaned())
