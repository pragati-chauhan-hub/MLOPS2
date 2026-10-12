# Data Dictionary – Student Performance Data Pipeline

## Dataset Source

| Item | Detail |
|------|--------|
| **Name** | UCI Student Performance Dataset |
| **Authors** | P. Cortez and A. Silva (2008) |
| **URL** | `https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip` |
| **File used** | `student-mat.csv` (Mathematics class, semicolon-delimited) |
| **Rows** | 395 student records |
| **Columns** | 33 source columns |
| **License** | CC BY 4.0 (UCI ML Repository) |
| **Raw landing** | `data/raw/student_mat_<timestamp>.csv` |

## Source Columns (UCI)

| Column | Type | Description |
|--------|------|-------------|
| `school` | string | Student's school: `GP` (Gabriel Pereira) or `MS` (Mousinho da Silveira) |
| `sex` | string | Student sex: `F` or `M` |
| `age` | integer | Student age (15–22) |
| `address` | string | Home address type: `U` (urban) or `R` (rural) |
| `famsize` | string | Family size: `LE3` (≤3) or `GT3` (>3) |
| `Pstatus` | string | Parent cohabitation: `T` (together) or `A` (apart) |
| `Medu` | integer | Mother's education level (0–4) |
| `Fedu` | integer | Father's education level (0–4) |
| `Mjob` | string | Mother's job: `teacher`, `health`, `services`, `at_home`, `other` |
| `Fjob` | string | Father's job: same categories as `Mjob` |
| `reason` | string | Reason for choosing school: `home`, `reputation`, `course`, `other` |
| `guardian` | string | Student guardian: `mother`, `father`, `other` |
| `traveltime` | integer | Home-to-school travel time (1=<15m … 4=>1h) |
| `studytime` | integer | Weekly study time (1=<2h … 4=>10h) |
| `failures` | integer | Number of past class failures (0–3, 4=n≥4) |
| `schoolsup` | string | Extra educational school support: `yes`/`no` |
| `famsup` | string | Family educational support: `yes`/`no` |
| `paid` | string | Extra paid classes: `yes`/`no` |
| `activities` | string | Extracurricular activities: `yes`/`no` |
| `nursery` | string | Attended nursery school: `yes`/`no` |
| `higher` | string | Wants higher education: `yes`/`no` |
| `internet` | string | Internet access at home: `yes`/`no` |
| `romantic` | string | In a romantic relationship: `yes`/`no` |
| `famrel` | integer | Quality of family relationships (1=very bad … 5=excellent) |
| `freetime` | integer | Free time after school (1=very low … 5=very high) |
| `goout` | integer | Going out with friends (1=very low … 5=very high) |
| `Dalc` | integer | Workday alcohol consumption (1=very low … 5=very high) |
| `Walc` | integer | Weekend alcohol consumption (1=very low … 5=very high) |
| `health` | integer | Current health status (1=very bad … 5=very good) |
| `absences` | integer | Number of school absences (0–93) |
| `G1` | integer | First period grade (0–20) |
| `G2` | integer | Second period grade (0–20) |
| `G3` | integer | Final grade (0–20) — **target variable** |

## Derived / Analytical Fields

These fields do not exist in the source; they are computed during the transformation step and loaded into `fact_student_performance`.

| Field | Type | Formula / Derivation | Meaning |
|-------|------|----------------------|---------|
| `student_id` | string | `S` + first 10 hex chars of SHA-256 of all source fields | Stable synthetic identifier (source has no ID) |
| `subject` | string | Constant `"mathematics"` | UCI subject represented by `student-mat.csv` |
| `semester` | string | Constant `"current"` | Placeholder; UCI has no semester field |
| `department` | string | Mapped from `Mjob`: teacher→Education & Social Sciences, health→Health & Life Sciences, services→Engineering & Technology, at_home→Arts & Humanities, other→Commerce & Business | Proxy academic department derived from mother's occupation |
| `attendance_percentage` | numeric | `100 × (1 − min(absences, 93) / 93)` | Attendance proxy; 93 is the observed source maximum absences |
| `average_internal_marks` | numeric | `mean(G1, G2)` | Average of the two internal assessment periods |
| `previous_grade` | numeric | `G1` | Prior-period performance proxy |
| `assignment_completion_rate` | numeric | `100 × (studytime / 4) × (1 − failures / 4)`, clipped [0, 100] | Proxy for engagement; combines study intensity with failure history |
| `pass_flag` | boolean | `G3 ≥ 10` | Binary pass indicator using the 10/20 threshold |
| `risk_flag` | boolean | `G3 < 10 OR attendance_percentage < 80 OR failures > 0` | Rule-based at-risk indicator |
| `risk_reason` | string | Semicolon-joined list of triggered rules: `final_mark_below_10`, `attendance_below_80_percent`, `prior_failures` | Human-readable triggered rules; `"no_rule_triggered"` when safe |
| `processed_at` | timestamp | UTC timestamp at transformation time | Audit / lineage field |

> **Transparency note**: The UCI dataset contains no attendance, assignment-completion, department, or semester columns. All derived columns use documented formulas and are presented as proxies, not observed measurements.

## Warehouse Tables

### Dimension Tables

| Table | Key | Description |
|-------|-----|-------------|
| `dim_student` | `student_key` | One row per unique student; natural key is `student_id` |
| `dim_subject` | `subject_key` | One row per subject (currently: `mathematics`) |
| `dim_semester` | `semester_key` | One row per semester (currently: `current`) |
| `dim_department` | `department_key` | One row per derived department (5 values) |

### Fact Table

| Table | Grain | Description |
|-------|-------|-------------|
| `fact_student_performance` | One row per student × subject × semester | Central analytical table; references all four dimensions |

### Analytical Marts

| Object | Type | Description |
|--------|------|-------------|
| `mart_high_risk_students` | Materialized View (PostgreSQL) / View (SQLite) | All rows where `risk_flag = TRUE`; joins student demographics from `dim_student` |
| `mart_student_summary` | View (both backends) | Aggregated per-student statistics: subject count, average final mark, average attendance, passed records count, and overall risk flag |

