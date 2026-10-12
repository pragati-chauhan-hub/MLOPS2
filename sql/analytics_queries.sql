-- ============================================================
-- Student Performance Data Pipeline – Analytical Queries
-- Part 1: Data Pipeline Implementation
-- All queries run against the PostgreSQL or SQLite warehouse.
-- ============================================================

-- 1. Overall pass / fail distribution
SELECT
    pass_flag,
    COUNT(*)                          AS students,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM fact_student_performance
GROUP BY pass_flag;

-- 2. Attendance vs final mark correlation
SELECT
    ROUND(CORR(attendance_percentage, g3)::numeric, 4) AS attendance_mark_correlation
FROM fact_student_performance;
-- SQLite alternative (no CORR): compute manually or use Python

-- 3. Subject-level pass/fail counts
SELECT
    subject,
    pass_flag,
    COUNT(*) AS students
FROM fact_student_performance
GROUP BY subject, pass_flag
ORDER BY subject, pass_flag;

-- 4. Department and semester comparison
SELECT
    department,
    semester,
    ROUND(AVG(g3), 2)                    AS average_final_mark,
    ROUND(AVG(attendance_percentage), 2) AS average_attendance,
    COUNT(*)                             AS student_records
FROM fact_student_performance
GROUP BY department, semester
ORDER BY department, semester;

-- 5. Grade progression: average G1 → G2 → G3 by pass/fail cohort
SELECT
    pass_flag,
    ROUND(AVG(g1), 2) AS avg_g1,
    ROUND(AVG(g2), 2) AS avg_g2,
    ROUND(AVG(g3), 2) AS avg_g3
FROM fact_student_performance
GROUP BY pass_flag;

-- 6. High-risk students (from the materialized view / SQLite view)
SELECT *
FROM mart_high_risk_students
ORDER BY attendance_percentage, final_mark;

-- 7. Risk reason breakdown – how many students triggered each rule
SELECT
    risk_reason,
    COUNT(*) AS student_count
FROM fact_student_performance
WHERE risk_flag = TRUE   -- PostgreSQL boolean; use 1 for SQLite
GROUP BY risk_reason
ORDER BY student_count DESC;

-- 8. Student-level aggregate summary (from summary mart)
SELECT *
FROM mart_student_summary
ORDER BY average_final_mark DESC;

-- 9. Top-10 performers by final mark
SELECT
    student_id,
    department,
    g1, g2, g3,
    attendance_percentage,
    risk_reason
FROM fact_student_performance
ORDER BY g3 DESC
LIMIT 10;

-- 10. Bottom-10 performers (highest dropout risk)
SELECT
    student_id,
    department,
    g1, g2, g3,
    attendance_percentage,
    risk_reason
FROM fact_student_performance
ORDER BY g3 ASC, attendance_percentage ASC
LIMIT 10;

