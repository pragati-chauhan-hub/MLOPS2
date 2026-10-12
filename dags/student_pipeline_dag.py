"""Airflow DAG – Student Performance Data Pipeline.

Orchestrates the full ETL workflow for the UCI Student Performance dataset:
  extract → validate → transform → load → build_analytics_mart

This DAG is intentionally free of any model-training or inference step (Part 1 only).
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from pendulum import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.extract import extract_dataset
from src.loading.load_to_postgres import database_url, load_dataset
from src.transformation.transform import latest_cleaned, transform_dataset
from src.validation.validate import latest_validated, validate_dataset

# ---------------------------------------------------------------------------
# Default task arguments
# ---------------------------------------------------------------------------
DEFAULT_ARGS = {
    "owner": "student_pipeline",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

DOC_MD = """
## Student Performance Pipeline – Part 1

| Step | Description |
|------|-------------|
| **extract** | Downloads `student-mat.csv` from the UCI ML Repository ZIP and saves a timestamped copy to `data/raw/`. Logs result to `logs/ingestion_log.csv`. |
| **validate** | Checks required columns, removes exact duplicates, rejects marks outside 0–20. Writes valid rows to `data/staging/` and rejected rows to `data/rejected/`. |
| **transform** | Derives `attendance_percentage`, `average_internal_marks`, `assignment_completion_rate`, `pass_flag`, `risk_flag`, `risk_reason`, and `department`. Saves to `data/cleaned/`. |
| **load** | Truncates and reloads PostgreSQL star-schema (dim_student, dim_subject, dim_semester, dim_department, fact_student_performance). Refreshes `mart_high_risk_students`. |
| **build_analytics_mart** | Explicit REFRESH of `mart_high_risk_students` materialized view (PostgreSQL). No-op on SQLite (view is recreated by load step). |

**Schedule**: `@weekly`  
**Dataset**: UCI ML Repository – Student Performance (Cortez & Silva, 2008)  
**Source URL**: `https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip`
"""


# ---------------------------------------------------------------------------
# Task callables
# ---------------------------------------------------------------------------
def extract_task() -> None:
    path = extract_dataset()
    if path is None:
        raise RuntimeError("Dataset extraction failed; see logs/ingestion_log.csv")


def validate_task() -> None:
    raw_files = sorted((PROJECT_ROOT / "data" / "raw").glob("student_*.csv"))
    if not raw_files:
        raise FileNotFoundError("No raw dataset found in data/raw/")
    validate_dataset(raw_files[-1])


def transform_task() -> None:
    transform_dataset(latest_validated())


def load_task() -> None:
    load_dataset(latest_cleaned())


def build_analytics_mart() -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url())
    with engine.begin() as connection:
        try:
            connection.execute(text("REFRESH MATERIALIZED VIEW mart_high_risk_students"))
        except Exception:
            # SQLite backend: the view is re-created during the load step; nothing to do here.
            pass
    engine.dispose()


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="student_performance_pipeline",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule="@weekly",
    catchup=False,
    tags=["education", "etl", "part1"],
    doc_md=DOC_MD,
    description="End-to-end ETL pipeline for the UCI Student Performance dataset (Part 1).",
) as dag:
    t_extract = PythonOperator(
        task_id="extract",
        python_callable=extract_task,
        doc_md="Download and save the raw UCI CSV to `data/raw/`.",
    )
    t_validate = PythonOperator(
        task_id="validate",
        python_callable=validate_task,
        doc_md="Validate schema, remove duplicates, reject out-of-range marks.",
    )
    t_transform = PythonOperator(
        task_id="transform",
        python_callable=transform_task,
        doc_md="Derive analytical features and risk flags; write to `data/cleaned/`.",
    )
    t_load = PythonOperator(
        task_id="load",
        python_callable=load_task,
        doc_md="Load star-schema dimensions and fact table into the data warehouse.",
    )
    t_mart = PythonOperator(
        task_id="build_analytics_mart",
        python_callable=build_analytics_mart,
        doc_md="Refresh the `mart_high_risk_students` materialized view (PostgreSQL).",
    )

    t_extract >> t_validate >> t_transform >> t_load >> t_mart

