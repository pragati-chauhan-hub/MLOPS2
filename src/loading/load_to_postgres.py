"""Load the analytical dataset into the data warehouse (PostgreSQL or SQLite)."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.utils.logging_config import DATA_ROOT, PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


def database_url() -> str:
    """Return the SQLAlchemy connection URL.

    Priority:
      1. DB_BACKEND=sqlite  -> local SQLite file (no server required)
      2. DATABASE_URL env   -> explicit full URL
      3. POSTGRES_* envs    -> construct PostgreSQL URL (default)
    """
    backend = os.getenv("DB_BACKEND", "sqlite").lower()
    if backend == "sqlite":
        db_path = DATA_ROOT / "student_dw.sqlite"
        return f"sqlite:///{db_path}"
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return (
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'student_user')}:{os.getenv('POSTGRES_PASSWORD', 'student_password')}"
        f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'student_dw')}"
    )


def _is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def load_dataset(input_path: str | Path) -> None:
    """Reload all dimension and fact tables (idempotent full-refresh)."""
    frame = pd.read_csv(input_path)
    engine = create_engine(database_url())
    sqlite = _is_sqlite(engine)

    if sqlite:
        with engine.begin() as conn:
            for tbl in ("fact_student_performance", "dim_student", "dim_subject",
                        "dim_semester", "dim_department"):
                conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
    else:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE fact_student_performance CASCADE"))
            conn.execute(text(
                "TRUNCATE TABLE dim_student, dim_subject, dim_semester, dim_department CASCADE"
            ))

    dim_student_cols = [c for c in ["student_id", "school", "sex", "age", "address", "famsize", "Pstatus"] if c in frame.columns]
    (
        frame[dim_student_cols]
        .rename(columns={"Pstatus": "pstatus"})
        .drop_duplicates("student_id")
        .to_sql("dim_student", engine, if_exists="append", index=False)
    )
    pd.DataFrame({"subject": frame["subject"].unique()}).to_sql("dim_subject", engine, if_exists="append", index=False)
    pd.DataFrame({"semester": frame["semester"].unique()}).to_sql("dim_semester", engine, if_exists="append", index=False)
    pd.DataFrame({"department": frame["department"].unique()}).to_sql("dim_department", engine, if_exists="append", index=False)

    fact_columns = [
        "student_id", "subject", "semester", "department",
        "G1", "G2", "G3",
        "attendance_percentage", "average_internal_marks", "assignment_completion_rate",
        "previous_grade", "pass_flag", "risk_flag", "risk_reason", "absences", "failures",
    ]
    available_fact_cols = [c for c in fact_columns if c in frame.columns]
    fact_frame = frame[available_fact_cols].rename(columns={"G1": "g1", "G2": "g2", "G3": "g3"}).copy()
    fact_frame["pass_flag"] = fact_frame["pass_flag"].astype(bool)
    fact_frame["risk_flag"] = fact_frame["risk_flag"].astype(bool)
    fact_frame.to_sql("fact_student_performance", engine, if_exists="append", index=False)

    if not sqlite:
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW mart_high_risk_students"))
    else:
        with engine.begin() as conn:
            conn.execute(text("DROP VIEW IF EXISTS mart_high_risk_students"))
            conn.execute(text("""
                CREATE VIEW mart_high_risk_students AS
                SELECT f.student_id, s.school, s.sex, s.age, f.subject, f.semester,
                       f.g3 AS final_mark, f.attendance_percentage, f.risk_reason, f.failures
                FROM fact_student_performance f
                JOIN dim_student s USING (student_id)
                WHERE f.risk_flag = 1
            """))
            conn.execute(text("DROP VIEW IF EXISTS mart_student_summary"))
            conn.execute(text("""
                CREATE VIEW mart_student_summary AS
                SELECT student_id,
                       count(*) AS subject_records,
                       round(avg(g3), 2) AS average_final_mark,
                       round(avg(attendance_percentage), 2) AS average_attendance,
                       max(CASE WHEN risk_flag THEN 1 ELSE 0 END) AS risk_flag,
                       sum(CASE WHEN pass_flag THEN 1 ELSE 0 END) AS passed_records
                FROM fact_student_performance
                GROUP BY student_id
            """))

    engine.dispose()


if __name__ == "__main__":
    from src.transformation.transform import latest_cleaned
    load_dataset(latest_cleaned())
