CREATE TABLE IF NOT EXISTS dim_student (
    student_key BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(32) UNIQUE NOT NULL,
    school VARCHAR(10), sex VARCHAR(10), age INTEGER, address VARCHAR(10), famsize VARCHAR(20), pstatus VARCHAR(10)
);
CREATE TABLE IF NOT EXISTS dim_subject (subject_key BIGSERIAL PRIMARY KEY, subject VARCHAR(50) UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS dim_semester (semester_key BIGSERIAL PRIMARY KEY, semester VARCHAR(50) UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS dim_department (department_key BIGSERIAL PRIMARY KEY, department VARCHAR(50) UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS fact_student_performance (
    performance_key BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(32) REFERENCES dim_student(student_id), subject VARCHAR(50), semester VARCHAR(50), department VARCHAR(50),
    g1 NUMERIC(5,2), g2 NUMERIC(5,2), g3 NUMERIC(5,2), attendance_percentage NUMERIC(5,2),
    average_internal_marks NUMERIC(5,2), assignment_completion_rate NUMERIC(5,2), previous_grade NUMERIC(5,2),
    pass_flag BOOLEAN, risk_flag BOOLEAN, risk_reason TEXT, absences INTEGER, failures INTEGER,
    UNIQUE(student_id, subject, semester)
);
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_high_risk_students AS
SELECT f.student_id, s.school, s.sex, s.age, f.subject, f.semester, f.g3 AS final_mark,
       f.attendance_percentage, f.risk_reason, f.failures
FROM fact_student_performance f JOIN dim_student s USING (student_id)
WHERE f.risk_flag = TRUE;

CREATE OR REPLACE VIEW mart_student_summary AS
SELECT student_id,
       count(*) AS subject_records,
       round(avg(g3), 2) AS average_final_mark,
       round(avg(attendance_percentage), 2) AS average_attendance,
       bool_or(risk_flag) AS risk_flag,
       sum(CASE WHEN pass_flag THEN 1 ELSE 0 END) AS passed_records
FROM fact_student_performance
GROUP BY student_id;
