"""Streamlit dashboard – Student Performance Observatory.

Views
-----
1. 🏠 Overview            – KPI cards + pass/fail/risk pie charts + sample table
2. 📈 Attendance vs Marks – scatter plot with OLS trendline
3. 🏢 Department Comparison – bar charts by department & semester
4. 📊 Grade Distribution   – histogram + box-plot for G1 / G2 / G3
5. 📚 Study-Time Analysis  – assignment completion rate vs final mark
6. ⚠️  Risk Register       – filtered high-risk student table + reason breakdown
7. 👤 Student Profile      – per-student grade trajectory line chart

Backend: SQLite (default, DB_BACKEND=sqlite) or PostgreSQL.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(_PROJECT_ROOT / ".env")

from src.loading.load_to_postgres import database_url

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Student Performance Observatory",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1rem 1.2rem;
  }
  [data-testid="stMetricValue"] { font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Student Observatory")
    st.caption("UCI Student Performance Dataset · Mathematics")
    st.divider()
    view = st.radio(
        "Navigate",
        [
            "🏠 Overview",
            "📈 Attendance vs Marks",
            "🏢 Department Comparison",
            "📊 Grade Distribution",
            "📚 Study-Time Analysis",
            "⚠️ Risk Register",
            "👤 Student Profile",
        ],
    )
    st.divider()
    backend = os.getenv("DB_BACKEND", "postgres").upper()
    st.caption(f"Backend: **{backend}**")

st.title("🎓 Student Performance Observatory")
st.caption(
    "End-to-end ETL pipeline · UCI Student Performance dataset · "
    "Part 1 – Data Pipeline Implementation"
)


# ── DB helpers ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    return create_engine(database_url())


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn)


try:
    performance = query("SELECT * FROM fact_student_performance")
    risk        = query("SELECT * FROM mart_high_risk_students")
except Exception as exc:
    st.error(f"⚠️ Could not load data: {exc}")
    st.info("Run the pipeline first:  `python run_pipeline.py`")
    st.stop()

if performance.empty:
    st.warning("No data found. Run the pipeline to populate the database.")
    st.code("python run_pipeline.py", language="bash")
    st.stop()

# Normalise bool columns that may be stored as int in SQLite
for col in ("pass_flag", "risk_flag"):
    if col in performance.columns:
        performance[col] = performance[col].astype(bool)
if "risk_flag" in risk.columns:
    risk["risk_flag"] = risk["risk_flag"].astype(bool)


# ── View 1 · Overview ───────────────────────────────────────────────────────
if view == "🏠 Overview":
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 Students",       performance["student_id"].nunique())
    c2.metric("📊 Avg Final Mark", f"{performance['g3'].mean():.2f} / 20")
    c3.metric("✅ Pass Rate",       f"{performance['pass_flag'].mean() * 100:.1f}%")
    c4.metric("⚠️ At-Risk",        f"{int(performance['risk_flag'].sum()):,}")
    c5.metric("📋 Records",        f"{len(performance):,}")
    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        pf = performance["pass_flag"].value_counts().reset_index()
        pf.columns = ["Outcome", "Count"]
        pf["Outcome"] = pf["Outcome"].map({True: "Pass (G3 ≥ 10)", False: "Fail (G3 < 10)"})
        fig_pie = px.pie(
            pf, names="Outcome", values="Count",
            title="Pass vs Fail",
            color_discrete_sequence=["#22c55e", "#ef4444"],
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_r:
        rf = performance["risk_flag"].value_counts().reset_index()
        rf.columns = ["Risk", "Count"]
        rf["Risk"] = rf["Risk"].map({True: "At-Risk", False: "Safe"})
        fig_rf = px.pie(
            rf, names="Risk", values="Count",
            title="Risk Flag Breakdown",
            color_discrete_sequence=["#f59e0b", "#6366f1"],
            hole=0.4,
        )
        st.plotly_chart(fig_rf, use_container_width=True)

    st.divider()
    st.subheader("Sample records (first 50)")
    st.dataframe(performance.head(50), use_container_width=True)


# ── View 2 · Attendance vs Marks ────────────────────────────────────────────
elif view == "📈 Attendance vs Marks":
    st.subheader("Attendance % vs Final Mark (G3)")
    try:
        fig = px.scatter(
            performance,
            x="attendance_percentage", y="g3",
            color="risk_flag",
            color_discrete_map={True: "#ef4444", False: "#6366f1"},
            hover_data=["student_id", "subject", "department"],
            trendline="ols",
            labels={
                "attendance_percentage": "Attendance %",
                "g3": "Final Mark (G3)",
                "risk_flag": "At-Risk",
            },
            opacity=0.75,
        )
    except Exception:
        fig = px.scatter(
            performance,
            x="attendance_percentage", y="g3",
            color="risk_flag",
            color_discrete_map={True: "#ef4444", False: "#6366f1"},
            hover_data=["student_id", "subject"],
            labels={
                "attendance_percentage": "Attendance %",
                "g3": "Final Mark (G3)",
            },
        )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    corr = performance["attendance_percentage"].corr(performance["g3"])
    col1.metric("Pearson Correlation (attendance ↔ G3)", f"{corr:.3f}")
    col2.metric(
        "Avg Attendance – At-Risk",
        f"{performance.loc[performance['risk_flag'], 'attendance_percentage'].mean():.1f}%",
    )
    col3.metric(
        "Avg Attendance – Safe",
        f"{performance.loc[~performance['risk_flag'], 'attendance_percentage'].mean():.1f}%",
    )


# ── View 3 · Department Comparison ──────────────────────────────────────────
elif view == "🏢 Department Comparison":
    st.subheader("Average Final Mark by Department")
    summary = performance.groupby(["department", "semester"], as_index=False).agg(
        average_mark=("g3", "mean"),
        average_attendance=("attendance_percentage", "mean"),
        student_count=("student_id", "nunique"),
    )
    fig_bar = px.bar(
        summary, x="department", y="average_mark",
        color="semester", barmode="group", text_auto=".2f",
        color_discrete_sequence=px.colors.qualitative.Vivid,
        labels={"average_mark": "Avg Final Mark (G3)", "department": "Department"},
    )
    fig_bar.update_layout(height=430)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Average Attendance % by Department")
    fig_att = px.bar(
        summary, x="department", y="average_attendance",
        color="semester", barmode="group", text_auto=".1f",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"average_attendance": "Avg Attendance %", "department": "Department"},
    )
    fig_att.update_layout(height=380)
    st.plotly_chart(fig_att, use_container_width=True)
    st.dataframe(summary.round(2), use_container_width=True)


# ── View 4 · Grade Distribution ─────────────────────────────────────────────
elif view == "📊 Grade Distribution":
    st.subheader("Grade Distribution across all periods")
    grade_melted = performance[["g1", "g2", "g3"]].melt(var_name="Period", value_name="Grade")
    grade_melted["Period"] = grade_melted["Period"].map(
        {"g1": "G1 – Period 1", "g2": "G2 – Period 2", "g3": "G3 – Final"}
    )

    fig_hist = px.histogram(
        grade_melted, x="Grade", color="Period",
        barmode="overlay", nbins=21, opacity=0.75,
        color_discrete_sequence=["#6366f1", "#22c55e", "#f59e0b"],
        labels={"Grade": "Mark (0–20)", "count": "Students"},
    )
    fig_hist.update_layout(height=420, bargap=0.05)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("Box-plot – spread of marks by period")
    fig_box = px.box(
        grade_melted, x="Period", y="Grade",
        color="Period",
        color_discrete_sequence=["#6366f1", "#22c55e", "#f59e0b"],
        points="outliers",
        labels={"Grade": "Mark (0–20)"},
    )
    fig_box.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig_box, use_container_width=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Mean G1 (Period 1)", f"{performance['g1'].mean():.2f}")
    col_b.metric("Mean G2 (Period 2)", f"{performance['g2'].mean():.2f}")
    col_c.metric("Mean G3 (Final)",    f"{performance['g3'].mean():.2f}")


# ── View 5 · Study-Time Analysis ─────────────────────────────────────────────
elif view == "📚 Study-Time Analysis":
    st.subheader("Assignment Completion Rate vs Final Mark")
    fig_acr = px.scatter(
        performance, x="assignment_completion_rate", y="g3",
        color="risk_flag",
        color_discrete_map={True: "#ef4444", False: "#6366f1"},
        labels={
            "assignment_completion_rate": "Assignment Completion Rate (%)",
            "g3": "Final Mark (G3)",
            "risk_flag": "At-Risk",
        },
        opacity=0.75,
    )
    fig_acr.update_layout(height=430)
    st.plotly_chart(fig_acr, use_container_width=True)

    corr2 = performance["assignment_completion_rate"].corr(performance["g3"])
    c1, c2 = st.columns(2)
    c1.metric("Pearson Correlation (ACR ↔ G3)", f"{corr2:.3f}")
    c2.metric("Avg ACR – At-Risk",
              f"{performance.loc[performance['risk_flag'], 'assignment_completion_rate'].mean():.1f}%")

    st.subheader("Average Internal Marks vs Final Mark")
    fig_aim = px.scatter(
        performance, x="average_internal_marks", y="g3",
        color="pass_flag",
        color_discrete_map={True: "#22c55e", False: "#ef4444"},
        labels={
            "average_internal_marks": "Avg Internal Marks (mean G1+G2)",
            "g3": "Final Mark (G3)",
            "pass_flag": "Passed",
        },
        opacity=0.75,
    )
    fig_aim.update_layout(height=380)
    st.plotly_chart(fig_aim, use_container_width=True)


# ── View 6 · Risk Register ──────────────────────────────────────────────────
elif view == "⚠️ Risk Register":
    st.subheader("High-Risk Students")
    max_att = st.sidebar.slider("Max attendance threshold (%)", 0, 100, 100, key="risk_att")
    filtered = risk.copy()
    if "attendance_percentage" in filtered.columns:
        filtered = filtered[filtered["attendance_percentage"] <= max_att]

    c1, c2, c3 = st.columns(3)
    c1.metric("At-risk students shown", len(filtered))
    if "final_mark" in filtered.columns:
        c2.metric("Avg Final Mark (at-risk)", f"{filtered['final_mark'].mean():.2f}")
    if "failures" in filtered.columns:
        c3.metric("Total prior failures", int(filtered["failures"].sum()))

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if "risk_reason" in risk.columns:
        st.subheader("Risk reason breakdown")
        reason_counts = risk["risk_reason"].value_counts().reset_index()
        reason_counts.columns = ["Reason", "Count"]
        fig_r = px.bar(
            reason_counts, x="Reason", y="Count",
            color="Reason",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_r.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_r, use_container_width=True)


# ── View 7 · Student Profile ─────────────────────────────────────────────────
else:
    st.subheader("Individual Student Profile")
    selected = st.selectbox("Select student ID", sorted(performance["student_id"].unique()))
    profile = performance[performance["student_id"] == selected].reset_index(drop=True)

    col_l, col_r = st.columns([1, 2])
    with col_l:
        display_cols = [
            c for c in ["subject", "semester", "g1", "g2", "g3",
                         "attendance_percentage", "pass_flag", "risk_flag"]
            if c in profile.columns
        ]
        st.dataframe(profile[display_cols], use_container_width=True)
        if "risk_reason" in profile.columns:
            st.markdown("**Risk reason:**")
            for reason in profile["risk_reason"].dropna().unique():
                if reason == "no_rule_triggered":
                    st.success("✅ No risk triggered")
                else:
                    st.warning(reason)
    with col_r:
        fig_line = px.line(
            profile, x="semester", y=["g1", "g2", "g3"],
            markers=True,
            color_discrete_sequence=["#6366f1", "#22c55e", "#f59e0b"],
            labels={"value": "Mark (0–20)", "variable": "Grade Period", "semester": "Semester"},
            title=f"Grade trajectory – {selected}",
        )
        fig_line.update_layout(height=400)
        st.plotly_chart(fig_line, use_container_width=True)
        if "attendance_percentage" in profile.columns:
            st.metric("Average Attendance", f"{profile['attendance_percentage'].mean():.1f}%")

