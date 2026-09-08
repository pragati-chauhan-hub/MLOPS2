# Data Dictionary

## Source

Primary source: UCI Student Performance Dataset, Cortez and Silva (2008), downloaded from `https://archive.ics.uci.edu/ml/machine-learning-databases/00320/student.zip`. The extraction step reads `student-mat.csv` as a semicolon-delimited file and preserves it in `data/raw/`.

## Analytical fields

| Field | Type | Source / transformation | Meaning |
|---|---|---|---|
| `student_id` | string | Deterministic SHA-256 of source identity fields | Synthetic stable identifier |
| `subject` | string | `mathematics` default | UCI subject represented by the file |
| `semester` | string | `current` default | Semester label; source has no semester field |
| `department` | string | `general` default | Placeholder dimension because UCI has no department |
| `G1`, `G2`, `G3` | numeric | UCI | First, second, and final-period grades, 0-20 |
| `attendance_percentage` | numeric | `100 * (1 - absences / 93)` | Proxy from UCI absence count; 93 is the observed source maximum |
| `average_internal_marks` | numeric | mean of G1 and G2 | Internal performance average |
| `assignment_completion_rate` | numeric | studytime and failures proxy | Estimated completion, not a source measurement |
| `previous_grade` | numeric | G1 | Previous-period performance proxy |
| `pass_flag` | boolean | G3 >= 10 | Passing threshold used by this project |
| `risk_flag` | boolean | G3 < 10 OR attendance < 80 OR failures > 0 | Transparent rule-based risk indicator, not ML |
| `risk_reason` | string | Same rules | Human-readable triggered rules |
| `absences`, `failures` | integer | UCI | Source absence count and prior class failures |

## Aggregate mart

`mart_student_summary` groups the fact table by `student_id` and provides subject-record count, average final mark, average attendance, whether any record is risky, and passed-record count.
