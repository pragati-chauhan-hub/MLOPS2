# Student Performance Data Pipeline
## MLOps Assignment – Part 1: Data Pipeline Implementation

End-to-end ETL pipeline for the **UCI Student Performance dataset**. This repository implements every Part 1 requirement: ingestion, validation, transformation, PostgreSQL (or SQLite) warehousing, Airflow orchestration, analytical marts, and a Streamlit dashboard. It intentionally contains **no model training, MLflow, FastAPI, or inference service** (those belong to Part 2).

---

## Submission Package Checklist

| Item | Location |
|------|---------|
| 1 · Source code and ETL scripts | `src/ingestion/`, `src/validation/`, `src/transformation/`, `src/loading/` |
| 2 · Airflow DAG | `dags/student_pipeline_dag.py` |
| 3 · Database schema and sample populated tables | `sql/schema.sql`, `data/student_dw.sqlite` |
| 4 · Dataset source information and access instructions | `docs/data_dictionary.md` → *Dataset Source* section |
| 5 · Architecture diagram and pipeline flow | `docs/architecture_diagram.md` |
| 6 · Data dictionary and validation rules | `docs/data_dictionary.md`, `docs/validation_rules.md` |
| 7 · Streamlit application (7 views) | `dashboard/app.py` → `streamlit run dashboard/app.py` |
| 8 · Rejected-record / error log | `data/rejected/`, `logs/ingestion_log.csv` |
| 9 · End-to-end execution evidence | `docs/execution_evidence.md` |
| 10 · README with setup and run instructions | **This file** |

---

## Dataset

| Field | Value |
|-------|-------|
| Name | UCI Student Performance Dataset |
| Authors | P. Cortez & A. Silva (2008) |
| URL | <https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip> |
| File | `student-mat.csv` (Mathematics, semicolon-delimited) |
| Rows | 395 records |
| Columns | 33 source + 11 derived analytical columns |
| License | CC BY 4.0 |

---

## Architecture

```
UCI ML Repository ZIP
       │
       ▼
src/ingestion/extract.py    →  data/raw/          (timestamped copies)
       │                        logs/ingestion_log.csv
       ▼
src/validation/validate.py  →  data/staging/      (valid rows)
                                data/rejected/     (rejected + reason)
       │
       ▼
src/transformation/transform.py → data/cleaned/   (analytical features)
       │
       ▼
src/loading/load_to_postgres.py → PostgreSQL / SQLite star-schema
                                    dim_student  dim_subject
                                    dim_semester dim_department
                                    fact_student_performance
                                    mart_high_risk_students (mat. view)
                                    mart_student_summary    (view)
       │
       ▼
dashboard/app.py  (Streamlit – 7 analytical views)
```

Orchestration: **Apache Airflow 2.10** DAG `student_performance_pipeline`  
DAG flow: `extract → validate → transform → load → build_analytics_mart`

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| pip | latest |
| PostgreSQL *(optional)* | 14+ |
| Docker Desktop + Compose *(optional)* | latest |

---

## Quick Start (SQLite – no Docker required)

By default, `DB_BACKEND=sqlite` is used (configured in `.env` or copied from `.env.example`), so the pipeline and dashboard run against a local SQLite file (`data/student_dw.sqlite`) with zero external database dependencies.

```powershell
# 1. Clone the repository
git clone https://github.com/pragati-chauhan-hub/MLOPS2.git
cd MLOPS2

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Copy environment template
Copy-Item .env.example .env

# 5. Run the full pipeline (downloads UCI data, validates, transforms, loads)
python run_pipeline.py

# 6. Launch the dashboard
streamlit run dashboard/app.py
# Open http://localhost:8501
```

That's it. The pipeline prints log lines for each of the 4 steps and confirms the output paths.

---

## PostgreSQL + Docker Setup

```powershell
# Copy the example env and set DB_BACKEND=postgres
Copy-Item .env.example .env
# Edit .env: set DB_BACKEND=postgres (default credentials already match docker-compose)

# Start PostgreSQL (schema auto-applied via docker-entrypoint-initdb.d/)
docker compose up -d postgres

# Run the pipeline
python run_pipeline.py

# Launch dashboard
streamlit run dashboard/app.py
```

### Verify the warehouse

```powershell
docker compose exec postgres psql -U student_user -d student_dw -c "\dt"
docker compose exec postgres psql -U student_user -d student_dw `
  -c "SELECT count(*) FROM fact_student_performance;"
docker compose exec postgres psql -U student_user -d student_dw `
  -c "SELECT * FROM mart_high_risk_students LIMIT 10;"
```

---

## Airflow Setup (Docker)

```powershell
docker compose up -d airflow
# Open http://localhost:8080  (admin / admin)
# Enable DAG: student_performance_pipeline
# Trigger manually → all 5 tasks should show green
docker compose down   # when finished
```

The DAG mounts `dags/`, `src/`, `data/`, and `logs/` into the container so it shares the same filesystem artifacts as the local runner.

---

## Individual Step Commands

```powershell
# Extract only
python -c "from src.ingestion.extract import extract_dataset; extract_dataset()"

# Validate the latest raw file
python -c "
from src.validation.validate import validate_dataset
from pathlib import Path
validate_dataset(sorted(Path('data/raw').glob('student_*.csv'))[-1])
"

# Transform the latest validated file
python -c "
from src.transformation.transform import transform_dataset, latest_cleaned
from pathlib import Path
transform_dataset(sorted(Path('data/staging').glob('validated_*.csv'))[-1])
"

# Load into database
python -c "
from src.loading.load_to_postgres import load_dataset
from src.transformation.transform import latest_cleaned
load_dataset(latest_cleaned())
"
```

---

## Dashboard Views

| # | View | Description |
|---|------|-------------|
| 1 | 🏠 Overview | KPI cards (students, avg mark, pass rate, at-risk, records) + pass/fail and risk-flag pie charts |
| 2 | 📈 Attendance vs Marks | Scatter plot with OLS trendline + Pearson correlation metrics |
| 3 | 🏢 Department Comparison | Grouped bar charts: avg mark and avg attendance by department/semester |
| 4 | 📊 Grade Distribution | Overlaid histogram + box-plot for G1, G2, G3 with mean metrics |
| 5 | 📚 Study-Time Analysis | ACR vs G3 scatter + Avg Internal Marks vs G3 scatter with pass/fail colour |
| 6 | ⚠️ Risk Register | Filterable at-risk student table + risk-reason breakdown bar chart |
| 7 | 👤 Student Profile | Per-student grade trajectory line chart + attendance metric |

---

## Running Tests

```powershell
python -m pytest tests -v
```

Expected: `2 passed` (plus deprecation warnings from pytest-asyncio on Python 3.14, which are not failures).

---

## Project Structure

```
MLOPS/
├── dags/
│   └── student_pipeline_dag.py      # Airflow DAG (5 tasks, @weekly, retries=2)
├── dashboard/
│   └── app.py                       # Streamlit dashboard (7 views)
├── data/
│   ├── raw/                         # Timestamped UCI downloads
│   ├── staging/                     # Validated rows
│   ├── cleaned/                     # Transformed analytical rows
│   ├── rejected/                    # Rejected records with reason column
│   └── student_dw.sqlite            # SQLite warehouse (local backend)
├── docs/
│   ├── architecture_diagram.md      # Mermaid pipeline + ER diagrams + tech stack
│   ├── data_dictionary.md           # All 33 source fields + 11 derived fields + mart tables
│   ├── validation_rules.md          # Validation rules (numbered)
│   └── execution_evidence.md        # Actual run output + row counts + test results
├── logs/
│   └── ingestion_log.csv            # Per-run extraction audit log
├── src/
│   ├── ingestion/extract.py         # Download UCI ZIP → data/raw/
│   ├── validation/validate.py       # Schema check, dedup, mark range → staging + rejected
│   ├── transformation/transform.py  # Feature engineering → data/cleaned/
│   ├── loading/load_to_postgres.py  # Star-schema load (PostgreSQL + SQLite)
│   └── utils/logging_config.py      # Shared logger and directory helpers
├── sql/
│   ├── schema.sql                   # DDL for all tables + materialized views
│   └── analytics_queries.sql        # 10 analytical SQL queries
├── tests/
│   └── test_pipeline.py             # pytest unit tests
├── .env                             # Local environment (DB_BACKEND=sqlite by default)
├── .env.example                     # Environment template
├── docker-compose.yml               # PostgreSQL 16 + Airflow 2.10
├── Dockerfile.airflow               # Airflow image with pipeline dependencies
├── requirements.txt                 # Python package pins
├── run_pipeline.py                  # Single-command local runner
└── README.md                        # This file
```

---

## Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_BACKEND` | `sqlite` | Use `sqlite` (local, no server) or `postgres` |
| `POSTGRES_HOST` | `localhost` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `student_dw` | Database name |
| `POSTGRES_USER` | `student_user` | Database user |
| `POSTGRES_PASSWORD` | `student_password` | Database password |
| `DATABASE_URL` | *(unset)* | Full SQLAlchemy URL (overrides POSTGRES_* vars) |

---

## Data Quality Checks

1. **Required columns**: `school`, `sex`, `age`, `G1`, `G2`, `G3` must exist.
2. **Deterministic ID**: SHA-256 of all source fields → `student_id`.
3. **Exact duplicate removal**: flagged `duplicate_record` in rejected CSV.
4. **Mark range validation**: G1/G2/G3 must be numeric and in [0, 20]; violations flagged `mark_out_of_range_or_non_numeric`.
5. **Risk rules**: `G3 < 10`, `attendance < 80%`, or `failures > 0` → `risk_flag = TRUE` + human-readable `risk_reason`.
6. **Zero silent drops**: every rejected row written to `data/rejected/` with a `reason` column.
7. **Idempotent load**: fact table truncated and reloaded on each run; materialized view refreshed.

See [`docs/validation_rules.md`](docs/validation_rules.md) for the full specification.

---

## References

- Cortez, P. and Silva, A. (2008). *Using Data Mining to Predict Secondary School Student Performance*. In A. Brito and J. Teixeira (Eds.), Proceedings of 5th Annual Future Business Technology Conference, Porto, Portugal, pp. 5-12.
- UCI ML Repository: <https://archive.ics.uci.edu/dataset/320/student+performance>

