# Student Performance Pipeline

Part 1 of the Student Performance and Dropout-Risk Prediction System: ingestion, validation, transformation, PostgreSQL warehousing, Airflow orchestration, and Streamlit analytics. This repository intentionally contains no model training, MLflow, FastAPI, or inference service.

## Architecture

See [docs/architecture_diagram.md](docs/architecture_diagram.md), [docs/data_dictionary.md](docs/data_dictionary.md), and [docs/validation_rules.md](docs/validation_rules.md).

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (local install or another managed instance)
- Docker Desktop and Docker Compose (optional convenience for PostgreSQL/Airflow)
- Git (optional)

Create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

The default `.env` values match the local PostgreSQL container. Do not commit `.env`.

## Reproduce the pipeline

1. Start PostgreSQL and Airflow if you are using the optional Compose environment:

```powershell
docker compose up -d postgres airflow
```

2. Run the file-based pipeline locally. The first command downloads `student-mat.csv` automatically from the documented UCI URL. The next commands reuse the latest output from each preceding layer:

```powershell
python -c "from src.ingestion.extract import extract_dataset; extract_dataset()"
python -c "from src.validation.validate import validate_dataset; from pathlib import Path; validate_dataset(sorted(Path('data/raw').glob('student_*.csv'))[-1])"
python -c "from src.transformation.transform import transform_dataset; from pathlib import Path; transform_dataset(sorted(Path('data/staging').glob('validated_*.csv'))[-1])"
python -c "from src.loading.load_to_postgres import load_dataset; from src.transformation.transform import latest_cleaned; load_dataset(latest_cleaned())"
```

3. Open Airflow at http://localhost:8080 with `admin` / `admin`, enable `student_performance_pipeline`, and trigger it. The DAG runs `extract -> validate -> transform -> load -> build_analytics_mart`.

4. Launch the dashboard:

```powershell
streamlit run dashboard/app.py
```

Open http://localhost:8501. All dashboard views query PostgreSQL, including the rule-based high-risk student mart.

## Evidence and checks

- Raw copies and ingestion status: `data/raw/` and `logs/ingestion_log.csv`
- Validated rows: `data/staging/`
- Rejected rows and reasons: `data/rejected/`
- Final analytical dataset: `data/cleaned/`
- Warehouse DDL: `sql/schema.sql`
- Unit tests: `python -m pytest tests`
- Recorded run evidence: [docs/execution_evidence.md](docs/execution_evidence.md)

The source has no attendance, assignment, department, or semester columns. The pipeline uses documented proxies/default dimensions, which are intentionally visible in the analytical output and dashboard rather than presented as observed source facts.

## PostgreSQL verification

```powershell
docker compose exec postgres psql -U student_user -d student_dw -c "\\dt"
docker compose exec postgres psql -U student_user -d student_dw -c "SELECT count(*) FROM fact_student_performance;"
docker compose exec postgres psql -U student_user -d student_dw -c "SELECT * FROM mart_high_risk_students LIMIT 10;"
```

Stop services when finished:

```powershell
docker compose down
```
