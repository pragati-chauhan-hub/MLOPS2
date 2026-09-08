"""Streamlit dashboard backed exclusively by PostgreSQL analytics tables."""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.loading.load_to_postgres import database_url

load_dotenv()
st.set_page_config(page_title="Student Performance", page_icon="SP", layout="wide")
st.title("Student Performance Observatory")
st.caption("UCI Student Performance | PostgreSQL analytical warehouse")

@st.cache_resource
def get_engine():
    return create_engine(database_url())

@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())

try:
    performance = query("SELECT * FROM fact_student_performance")
    risk = query("SELECT * FROM mart_high_risk_students")
except Exception as exc:
    st.error(f"Could not connect to PostgreSQL: {exc}")
    st.stop()

view = st.sidebar.radio("View", ["Overview", "Attendance vs marks", "Pass/fail by subject", "Department comparison", "Risk register", "Student profile"])

if view == "Overview":
    columns = st.columns(4)
    columns[0].metric("Students", performance["student_id"].nunique())
    columns[1].metric("Average final mark", f"{performance['g3'].mean():.1f}/20")
    columns[2].metric("Pass rate", f"{performance['pass_flag'].mean() * 100:.1f}%")
    columns[3].metric("Risk flagged", f"{performance['risk_flag'].sum():,}")
    st.dataframe(performance.head(25), use_container_width=True)

elif view == "Attendance vs marks":
    st.subheader("Attendance and final marks")
    fig = px.scatter(performance, x="attendance_percentage", y="g3", color="risk_flag", hover_data=["student_id", "subject"], trendline="ols")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Correlation", f"{performance['attendance_percentage'].corr(performance['g3']):.3f}")

elif view == "Pass/fail by subject":
    counts = performance.assign(result=performance["pass_flag"].map({True: "Pass", False: "Fail"})).groupby(["subject", "result"], as_index=False).size()
    st.plotly_chart(px.bar(counts, x="subject", y="size", color="result", barmode="group"), use_container_width=True)

elif view == "Department comparison":
    summary = performance.groupby(["department", "semester"], as_index=False).agg(average_mark=("g3", "mean"), average_attendance=("attendance_percentage", "mean"))
    st.plotly_chart(px.bar(summary, x="department", y="average_mark", color="semester", barmode="group"), use_container_width=True)
    st.dataframe(summary, use_container_width=True)

elif view == "Risk register":
    minimum_attendance = st.sidebar.slider("Minimum attendance", 0, 100, 80)
    filtered = risk[risk["attendance_percentage"] < minimum_attendance]
    st.subheader("Rule-based high-risk students")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

else:
    selected = st.selectbox("Student", sorted(performance["student_id"].unique()))
    profile = performance[performance["student_id"] == selected]
    st.dataframe(profile, use_container_width=True, hide_index=True)
    st.plotly_chart(px.line(profile, x="semester", y=["g1", "g2", "g3"], markers=True), use_container_width=True)
