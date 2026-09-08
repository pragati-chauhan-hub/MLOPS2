"""Airflow orchestration for the student performance data pipeline."""
from __future__ import annotations

import sys
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


def extract_task() -> None:
    if extract_dataset() is None:
        raise RuntimeError("Dataset extraction failed; see logs/ingestion_log.csv")


def validate_task() -> None:
    raw_files = sorted((PROJECT_ROOT / "data" / "raw").glob("student_*.csv"))
    if not raw_files:
        raise FileNotFoundError("No raw dataset found")
    validate_dataset(raw_files[-1])


def transform_task() -> None:
    transform_dataset(latest_validated())


def load_task() -> None:
    load_dataset(latest_cleaned())


def build_analytics_mart() -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url())
    with engine.begin() as connection:
        connection.execute(text("REFRESH MATERIALIZED VIEW mart_high_risk_students"))
    engine.dispose()

with DAG(
    dag_id="student_performance_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@weekly",
    catchup=False,
    tags=["education", "etl"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_task)
    validate = PythonOperator(task_id="validate", python_callable=validate_task)
    transform = PythonOperator(task_id="transform", python_callable=transform_task)
    load = PythonOperator(task_id="load", python_callable=load_task)
    mart = PythonOperator(task_id="build_analytics_mart", python_callable=build_analytics_mart)
    extract >> validate >> transform >> load >> mart
