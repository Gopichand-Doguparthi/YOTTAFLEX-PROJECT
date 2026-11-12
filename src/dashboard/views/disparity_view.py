"""
View 6: Disparity Detection and Evidence View.
Evaluates multi-factor compensation disparities against peer cohorts and performance evidence.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand, PerformanceEvidence, Tenure
from src.engine.disparity_detector import DisparityDetector
from src.dashboard.views.helpers import get_role_map, get_level_map, get_location_map, PLOTLY_CONFIG


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Multi-Factor Disparity Detection & Evidence Analysis")
    st.markdown("Identifies unexplained compensation disparities benchmarked against peer cohort medians, documented performance ratings, and tenure.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    status_filter = st.selectbox(
        "Filter by Disparity Outcome Status:",
        ["All Outcomes", "UNEXPLAINED_DISPARITY", "MANUAL_REVIEW_REQUIRED", "EXPLAINED_VARIATION", "INSUFFICIENT_EVIDENCE"],
        index=0
    )

    detector = DisparityDetector()

    emp_query = db.query(Employee)
    if selected_role != "All":
        emp_query = emp_query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        emp_query = emp_query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        emp_query = emp_query.filter(Employee.current_location_id == selected_location)
    employees = emp_query.all()

    salaries = db.query(SalaryRecord).filter(SalaryRecord.effective_date >= "2026-01-01").all()
    latest_sals = {s.employee_id: s for s in salaries}

    bands = db.query(CompensationBand).filter(CompensationBand.status == "ACTIVE").all()
    band_lookup = {(b.role_id, b.level_id, b.location_id): b for b in bands}

    cohort_salaries = {}
    for emp in employees:
        sal = latest_sals.get(emp.employee_id)
        if sal:
            key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
            cohort_salaries.setdefault(key, []).append(sal.normalized_salary)

    cohort_medians = {k: float(np.median(v)) for k, v in cohort_salaries.items()}
    cohort_sizes = {k: len(v) for k, v in cohort_salaries.items()}

    perfs = db.query(PerformanceEvidence).all()
    latest_perf = {}
    for p in perfs:
        if p.employee_id not in latest_perf or p.effective_date > latest_perf[p.employee_id].effective_date:
            latest_perf[p.employee_id] = p

    tenures = {t.employee_id: t for t in db.query(Tenure).all()}

    findings = []
    for emp in employees:
        sal = latest_sals.get(emp.employee_id)
        if not sal:
            continue

        cohort_key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
        med_sal = cohort_medians.get(cohort_key, sal.normalized_salary)
        size = cohort_sizes.get(cohort_key, 1)

        band = band_lookup.get((emp.current_role_id, emp.current_level_id, emp.current_location_id))
        b_min = band.min_salary if band else (med_sal * 0.8)
        b_mid = band.mid_salary if band else med_sal
        b_max = band.max_salary if band else (med_sal * 1.2)

        perf = latest_perf.get(emp.employee_id)
        rating = perf.rating_score if perf else None
        tenure_rec = tenures.get(emp.employee_id)
        c_tenure = tenure_rec.tenure_in_company_years if tenure_rec else 1.0
        r_tenure = tenure_rec.tenure_in_role_years if tenure_rec else 1.0

        res = detector.evaluate_employee(
            employee_id=emp.employee_id,
            normalized_salary=sal.normalized_salary,
            band_min=b_min,
            band_mid=b_mid,
            band_max=b_max,
            cohort_median_salary=med_sal,
            cohort_size=size,
            performance_rating=rating,
            tenure_in_role_years=r_tenure,
            tenure_in_company_years=c_tenure
        )

        findings.append({
            "Employee ID": emp.employee_id,
            "Name": f"{emp.first_name} {emp.last_name}",
            "Department": emp.department,
            "Role": role_map.get(emp.current_role_id, emp.current_role_id),
            "Level": level_map.get(emp.current_level_id, emp.current_level_id),
            "Location": loc_map.get(emp.current_location_id, emp.current_location_id),
            "Salary (USD)": sal.normalized_salary,
            "Cohort Median": med_sal,
            "Deviation (%)": res.deviation_from_cohort_median_pct,
            "Compa-Ratio": res.compa_ratio,
            "Rating": rating,
            "Company Tenure (yrs)": c_tenure,
            "Status": res.status,
            "Primary Reason": res.primary_reason,
            "Is Disparity": res.is_disparity
        })

    df = pd.DataFrame(findings)
    if df.empty:
        st.info("No employee records available for disparity evaluation.")
        return

    unexplained_count = len(df[df["Status"] == "UNEXPLAINED_DISPARITY"])
    review_count = len(df[df["Status"] == "MANUAL_REVIEW_REQUIRED"])
    explained_count = len(df[df["Status"] == "EXPLAINED_VARIATION"])
    insufficient_count = len(df[df["Status"] == "INSUFFICIENT_EVIDENCE"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unexplained Disparities", f"{unexplained_count}", delta=f"{unexplained_count} flagged", delta_color="inverse")
    col2.metric("Manual Review Required", f"{review_count}", "Mixed signals detected")
    col3.metric("Explained Variations", f"{explained_count}", "Supported by merit or tenure")
    col4.metric("Insufficient Evidence", f"{insufficient_count}", "Cohort too small to conclude")

    st.markdown("---")

    col_pie, col_scatter = st.columns(2)
    with col_pie:
        status_dist = df["Status"].value_counts().reset_index()
        status_dist.columns = ["Status", "Count"]
        fig_pie = px.pie(
            status_dist,
            names="Status",
            values="Count",
            title="Compensation Equity Evaluation Classification",
            color="Status",
            color_discrete_map={
                "UNEXPLAINED_DISPARITY": "#e74c3c",
                "MANUAL_REVIEW_REQUIRED": "#f39c12",
                "EXPLAINED_VARIATION": "#2ecc71",
                "INSUFFICIENT_EVIDENCE": "#95a5a6"
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_scatter:
        fig_disp = px.scatter(
            df,
            x="Rating",
            y="Deviation (%)",
            color="Status",
            hover_data=["Employee ID", "Name", "Salary (USD)"],
            title="Performance Rating vs Cohort Deviation (%)",
            color_discrete_map={
                "UNEXPLAINED_DISPARITY": "#e74c3c",
                "MANUAL_REVIEW_REQUIRED": "#f39c12",
                "EXPLAINED_VARIATION": "#2ecc71",
                "INSUFFICIENT_EVIDENCE": "#95a5a6"
            }
        )
        fig_disp.add_hline(y=-15.0, line_dash="dash", line_color="red", annotation_text="Disparity Threshold (-15%)")
        fig_disp.add_vline(x=3.5, line_dash="dash", line_color="blue", annotation_text="High Performer (3.5+)")
        st.plotly_chart(fig_disp, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Disparity Evaluation Findings")
    filtered_df = df if status_filter == "All Outcomes" else df[df["Status"] == status_filter]
    st.dataframe(filtered_df, use_container_width=True)
