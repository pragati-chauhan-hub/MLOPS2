# Architecture Diagram – Student Performance Data Pipeline

## High-Level Pipeline Flow

```mermaid
flowchart TD
    subgraph SOURCE["📦 Data Source"]
        UCI["UCI ML Repository\nstudent-mat.csv (semicolon CSV)\n395 rows · 33 columns"]
    end

    subgraph INGEST["🔽 Ingestion Layer  (src/ingestion/extract.py)"]
        DL["urllib.urlopen\ndownload ZIP"]
        RAW["data/raw/\nstudent_mat_YYYYMMDDTHHMMSSZ.csv\n(timestamped, untouched)"]
        LOG["logs/ingestion_log.csv\nextracted_at · source · status · row_count · error"]
        DL --> RAW
        DL --> LOG
    end

    subgraph VALIDATE["✅ Validation Layer  (src/validation/validate.py)"]
        V1["Schema check\n(6 required columns)"]
        V2["Duplicate removal\n(exact-row dedup)"]
        V3["Mark range check\nG1/G2/G3 ∈ [0, 20]"]
        STAGING["data/staging/\nvalidated_YYYYMMDDTHHMMSSZ.csv"]
        REJECT["data/rejected/\nrejected_records_YYYYMMDDTHHMMSSZ.csv\n(reason column)"]
        V1 --> V2 --> V3
        V3 --> STAGING
        V3 --> REJECT
    end

    subgraph TRANSFORM["⚙️ Transformation Layer  (src/transformation/transform.py)"]
        T1["attendance_percentage\n= 100 × (1 − absences/93)"]
        T2["average_internal_marks\n= mean(G1, G2)"]
        T3["assignment_completion_rate\n= studytime/failures proxy"]
        T4["department mapping\nMjob → 5 academic departments"]
        T5["pass_flag: G3 ≥ 10\nrisk_flag: G3<10 OR att<80 OR failures>0\nrisk_reason: human-readable rules"]
        CLEANED["data/cleaned/\nstudent_performance_YYYYMMDDTHHMMSSZ.csv"]
        T1 & T2 & T3 & T4 & T5 --> CLEANED
    end

    subgraph WAREHOUSE["🗄️ Data Warehouse  (PostgreSQL / SQLite)"]
        DIM_STU["dim_student\n(student_key, student_id, school, sex, age, address, famsize, pstatus)"]
        DIM_SUB["dim_subject\n(subject_key, subject)"]
        DIM_SEM["dim_semester\n(semester_key, semester)"]
        DIM_DEP["dim_department\n(department_key, department)"]
        FACT["fact_student_performance\n(performance_key + FKs + g1/g2/g3 +\nattendance_percentage + pass_flag + risk_flag + risk_reason)"]
        MART_RISK["mart_high_risk_students\n(Materialized View / SQLite View)\nrisk_flag = TRUE rows with student demographics"]
        MART_SUM["mart_student_summary\n(View) – per-student aggregates"]
        DIM_STU & DIM_SUB & DIM_SEM & DIM_DEP --> FACT
        FACT --> MART_RISK
        FACT --> MART_SUM
    end

    subgraph ORCHESTRATION["🔄 Orchestration  (Apache Airflow 2.10)"]
        DAG["student_performance_pipeline DAG\n@weekly · retries=2 · retry_delay=5 min"]
        T_EXT["extract task"]
        T_VAL["validate task"]
        T_TRF["transform task"]
        T_LOD["load task"]
        T_MRT["build_analytics_mart task"]
        DAG --> T_EXT --> T_VAL --> T_TRF --> T_LOD --> T_MRT
    end

    subgraph DASHBOARD["📊 Analytics Dashboard  (Streamlit)"]
        D1["🏠 Overview\nKPI cards + pie charts"]
        D2["📈 Attendance vs Marks\nscatter + OLS trendline"]
        D3["🏢 Department Comparison\nbar charts"]
        D4["📊 Grade Distribution\nhistogram + box-plot"]
        D5["📚 Study-Time Analysis\nscatter plots"]
        D6["⚠️ Risk Register\nfiltered table + reason bar chart"]
        D7["👤 Student Profile\nline chart trajectory"]
    end

    UCI --> DL
    RAW --> V1
    STAGING --> T1
    CLEANED --> FACT
    MART_RISK & MART_SUM --> D1 & D2 & D3 & D4 & D5 & D6 & D7
    T_EXT --> RAW
    T_VAL --> STAGING & REJECT
    T_TRF --> CLEANED
    T_LOD --> WAREHOUSE
    T_MRT --> MART_RISK
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Data manipulation | pandas 2.2 |
| Orchestration | Apache Airflow 2.10 (Docker or local) |
| Database | PostgreSQL 16 (primary) · SQLite (local fallback) |
| ORM / connection | SQLAlchemy 2.0 + psycopg2-binary |
| Dashboard | Streamlit 1.41 + Plotly 5.24 |
| Containerisation | Docker Compose (optional) |
| Testing | pytest 8 |
| Environment | python-dotenv |

## Data Layer Lineage

```
data/raw/           ← untouched timestamped copies from UCI
data/staging/       ← validated rows (schema OK, no duplicates, marks in range)
data/rejected/      ← rows with reason column explaining rejection
data/cleaned/       ← fully transformed analytical dataset
PostgreSQL/SQLite   ← star-schema warehouse + analytical marts
```

## Warehouse Star Schema

```mermaid
erDiagram
    dim_student {
        bigint student_key PK
        varchar student_id UK
        varchar school
        varchar sex
        int age
        varchar address
        varchar famsize
        varchar pstatus
    }
    dim_subject {
        bigint subject_key PK
        varchar subject UK
    }
    dim_semester {
        bigint semester_key PK
        varchar semester UK
    }
    dim_department {
        bigint department_key PK
        varchar department UK
    }
    fact_student_performance {
        bigint performance_key PK
        varchar student_id FK
        varchar subject
        varchar semester
        varchar department
        numeric g1
        numeric g2
        numeric g3
        numeric attendance_percentage
        numeric average_internal_marks
        numeric assignment_completion_rate
        numeric previous_grade
        boolean pass_flag
        boolean risk_flag
        text risk_reason
        int absences
        int failures
    }
    dim_student ||--o{ fact_student_performance : "student_id"
    dim_subject ||--o{ fact_student_performance : "subject"
    dim_semester ||--o{ fact_student_performance : "semester"
    dim_department ||--o{ fact_student_performance : "department"
```
