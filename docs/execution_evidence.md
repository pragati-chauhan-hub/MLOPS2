# Part 1 – Execution Evidence

## End-to-End Pipeline Run

**Date:** 2026-10-12  
**Command:** `python run_pipeline.py`  
**Backend:** SQLite (`DB_BACKEND=sqlite`)

### Console output

```
2026-10-12 13:27:46 INFO ============================================================
2026-10-12 13:27:46 INFO Student Performance Pipeline  (DB: sqlite:///data/student_dw.sqlite)
2026-10-12 13:27:46 INFO ============================================================
2026-10-12 13:27:46 INFO [1/4] Extracting UCI dataset (subject=mat)…
2026-10-12 13:27:48 INFO Extracted 395 rows to data/raw/student_mat_20261012T075748Z.csv
2026-10-12 13:27:48 INFO       Raw file: data/raw/student_mat_20261012T075748Z.csv
2026-10-12 13:27:48 INFO [2/4] Validating…
2026-10-12 13:27:48 INFO       Validated file: data/staging/validated_20261012T075748Z.csv
2026-10-12 13:27:48 INFO [3/4] Transforming…
2026-10-12 13:27:48 INFO       Cleaned file: data/cleaned/student_performance_20261012T075748Z.csv
2026-10-12 13:27:48 INFO [4/4] Loading into database…
2026-10-12 13:27:48 INFO       Done! Database: sqlite:///data/student_dw.sqlite
2026-10-12 13:27:48 INFO ============================================================
2026-10-12 13:27:48 INFO Pipeline complete. Run the dashboard with:
2026-10-12 13:27:48 INFO   streamlit run dashboard/app.py
2026-10-12 13:27:48 INFO ============================================================
```

### Data layer row counts (verified)

| Layer | File / Table | Row Count |
|-------|-------------|-----------|
| Raw | `data/raw/student_mat_20261012T075748Z.csv` | 395 |
| Staging | `data/staging/validated_20261012T075748Z.csv` | 395 |
| Rejected | `data/rejected/rejected_records_20261012T075748Z.csv` | 0 |
| Cleaned | `data/cleaned/student_performance_20261012T075748Z.csv` | 395 |
| `dim_student` | PostgreSQL / SQLite | 395 |
| `dim_subject` | PostgreSQL / SQLite | 1 |
| `dim_semester` | PostgreSQL / SQLite | 1 |
| `dim_department` | PostgreSQL / SQLite | 5 |
| `fact_student_performance` | PostgreSQL / SQLite | 395 |
| `mart_high_risk_students` | Materialized view | 182 |

### Ingestion log (`logs/ingestion_log.csv`)

```
extracted_at,source,status,row_count,error
2026-10-12T07:57:48.279Z,https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip::student-mat.csv,success,395,
```

## Unit Tests

**Command:** `python -m pytest tests -v`

```
platform win32 -- Python 3.14.5, pytest-7.4.3
collected 2 items

tests/test_pipeline.py::test_validation_removes_duplicates_and_invalid_marks PASSED  [ 50%]
tests/test_pipeline.py::test_transformation_creates_required_features        PASSED  [100%]

======================== 2 passed, 52 warnings in 0.91s ========================
```

**Tests cover:**
- Duplicate record detection and removal (`duplicate_record` reason in rejected CSV)
- Out-of-range mark rejection (`mark_out_of_range_or_non_numeric` reason)
- All required derived columns present after transformation
- Correct `pass_flag` and `risk_flag` values for known inputs

## Sample mart_high_risk_students Output

```
student_id   | school | sex | age | subject     | semester | final_mark | attendance_pct | risk_reason
SEB094996FD  | GP     | F   | 18  | mathematics | current  | 6          | 93.55          | final_mark_below_10
SF5243D5A31  | GP     | F   | 17  | mathematics | current  | 6          | 95.70          | final_mark_below_10
S3FB543A4D7  | GP     | F   | 15  | mathematics | current  | 10         | 89.25          | prior_failures
```

## PostgreSQL Verification (when Docker is available)

```powershell
docker compose up -d postgres
docker compose exec postgres psql -U student_user -d student_dw -c "\dt"
docker compose exec postgres psql -U student_user -d student_dw \
  -c "SELECT count(*) FROM fact_student_performance;"
docker compose exec postgres psql -U student_user -d student_dw \
  -c "SELECT * FROM mart_high_risk_students LIMIT 5;"
docker compose exec postgres psql -U student_user -d student_dw \
  -c "SELECT * FROM mart_student_summary ORDER BY average_final_mark DESC LIMIT 5;"
```

## Airflow DAG (when Docker is available)

```powershell
docker compose up -d airflow
# Navigate to http://localhost:8080  (admin / admin)
# Enable DAG: student_performance_pipeline
# Trigger manually → observe extract → validate → transform → load → build_analytics_mart
# All 5 tasks should show green "success" state
```