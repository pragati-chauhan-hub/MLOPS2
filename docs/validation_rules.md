# Validation Rules – Student Performance Data Pipeline

All validation is performed in `src/validation/validate.py`. Every rejected record is written to a timestamped CSV in `data/rejected/` with an explicit `reason` column. No row is ever silently dropped.

## Rules

| # | Rule | Error Code | Action |
|---|------|-----------|--------|
| 1 | Source file must contain columns: `school`, `sex`, `age`, `G1`, `G2`, `G3` | `schema_error` (raises immediately) | Pipeline stops; logged to `logs/ingestion_log.csv` |
| 2 | A deterministic `student_id` is generated from SHA-256 of all source fields | *(not a rejection rule)* | Applied to every row before further checks |
| 3 | Exact duplicate rows (all columns identical) are detected | `duplicate_record` | Duplicate rows → rejected CSV; first occurrence is kept |
| 4 | `G1`, `G2`, and `G3` must each be numeric (parseable as float) | `mark_out_of_range_or_non_numeric` | Non-numeric or NaN mark rows → rejected CSV |
| 5 | `G1`, `G2`, and `G3` must each be in the closed range [0, 20] | `mark_out_of_range_or_non_numeric` | Out-of-range rows → rejected CSV; shared error code with rule 4 |
| 6 | Missing attendance / assignment / department fields do not cause rejection | *(by design)* | These fields do not exist in the UCI source; analytical proxies are derived in the transformation step |
| 7 | Every rejected record is written to `data/rejected/rejected_records_<timestamp>.csv` with a `reason` column | *(output)* | Even zero-rejection runs produce an empty rejected file with the header row |

## Rejection Log Format

`data/rejected/rejected_records_<timestamp>.csv`

```
student_id, school, sex, age, G1, G2, G3, ..., source_file, validation_status, reason
S<hash>,   GP,     F,   17,  12, 13, 14, ..., student_mat_<ts>.csv, valid, duplicate_record
S<hash>,   MS,     M,   18,  21, 10, 9,  ..., student_mat_<ts>.csv, valid, mark_out_of_range_or_non_numeric
```

## Ingestion Log Format

`logs/ingestion_log.csv`

```
extracted_at, source, status, row_count, error
2026-10-12T07:57:48Z, https://.../student.zip::student-mat.csv, success, 395,
```

## Risk Classification Rules

Applied after validation, during the transformation step (`src/transformation/transform.py`):

| Flag | Condition | `risk_reason` value |
|------|-----------|---------------------|
| `risk_flag = TRUE` | `G3 < 10` | `final_mark_below_10` |
| `risk_flag = TRUE` | `attendance_percentage < 80` | `attendance_below_80_percent` |
| `risk_flag = TRUE` | `failures > 0` | `prior_failures` |
| `risk_flag = TRUE` | Multiple conditions | Semicolon-joined list of all triggered rules |
| `risk_flag = FALSE` | No condition triggered | `no_rule_triggered` |

These are transparent, rule-based flags. No machine learning is used in Part 1.

