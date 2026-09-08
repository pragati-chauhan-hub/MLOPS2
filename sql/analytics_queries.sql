-- Attendance and marks correlation
SELECT corr(attendance_percentage, G3) AS attendance_mark_correlation FROM fact_student_performance;
-- Subject pass/fail distribution
SELECT subject, pass_flag, count(*) AS students FROM fact_student_performance GROUP BY subject, pass_flag;
-- Department/semester comparison
SELECT department, semester, round(avg(G3), 2) AS average_final_mark, round(avg(attendance_percentage), 2) AS average_attendance
FROM fact_student_performance GROUP BY department, semester ORDER BY department, semester;
-- High-risk students
SELECT * FROM mart_high_risk_students ORDER BY attendance_percentage, final_mark;
-- Student-level aggregate
SELECT * FROM mart_student_summary ORDER BY average_final_mark DESC;
