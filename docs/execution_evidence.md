# Part 1 Execution Evidence

## Verified locally

Date: 2026-09-07

Command:

```powershell
python -m pytest tests
```

Result: `2 passed, 50 warnings in 1.60s`.

The warnings are `pytest-asyncio` / Python 3.14 deprecation warnings and are not test failures.

The tests cover duplicate removal, invalid-mark rejection, required rejection reasons, and creation of the analytical feature columns and rule-based flags.

Command:

```powershell
python -c "from src.ingestion.extract import extract_dataset; from src.validation.validate import validate_dataset; from src.transformation.transform import transform_dataset; raw=extract_dataset(); assert raw is not None; staging=validate_dataset(raw); cleaned=transform_dataset(staging); print(f'raw={raw}'); print(f'staging={staging}'); print(f'cleaned={cleaned}')"
```

Result: UCI `student-mat.csv` extracted successfully with 395 rows. The run created timestamped raw, staging, and cleaned files. A follow-up artifact check confirmed 395 rows in each layer, zero rejected rows, a successful `logs/ingestion_log.csv` entry, and the required analytical features.

## Environment-dependent verification

The following steps require PostgreSQL and are intentionally separate from the verified Python file pipeline:

```powershell
python -c "from src.loading.load_to_postgres import load_dataset; from src.transformation.transform import latest_cleaned; load_dataset(latest_cleaned())"
streamlit run dashboard/app.py
```

When Airflow is available, trigger `student_performance_pipeline` and capture the DAG graph and task success state. Docker is optional for Part 1; the same SQL schema and application commands can use a local PostgreSQL installation configured through `.env`.