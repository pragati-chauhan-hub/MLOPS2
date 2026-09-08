# Validation Rules

1. Required source columns (`school`, `sex`, `age`, `G1`, `G2`, `G3`) must exist; otherwise the run stops with a clear schema error.
2. A deterministic `student_id` is generated because the source has no identifier.
3. Exact duplicate records after ingestion are rejected with `duplicate_record`.
4. `G1`, `G2`, and `G3` must be numeric values from 0 through 20; invalid rows are rejected with `mark_out_of_range_or_non_numeric`.
5. Missing attendance and assignment values do not occur in this source because those fields do not exist. Their analytical proxies are derived from `absences`, `studytime`, and `failures`, and are documented in the data dictionary.
6. Every rejected record is written to a timestamped CSV with a `reason` column. No row is silently dropped.
7. Analytical outputs retain student-level rows in the fact table and expose student-level aggregates through `mart_student_summary`.
