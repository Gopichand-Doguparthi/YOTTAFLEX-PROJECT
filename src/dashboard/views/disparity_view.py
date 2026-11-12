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
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    PLOTLY_CONFIG, apply_clean_layout,
)


_STATUS_LABELS = {
    "UNEXPLAINED_DISPARITY": "Unexplained Disparity",
    "MANUAL_REVIEW_REQUIRED": "Manual Review Required",
    "EXPLAINED_VARIATION": "Explained Variation",
    "INSUFFICIENT_EVIDENCE": "Insufficient Evidence",
}

_STATUS_COLORS = {
    "Unexplained Disparity": "#e74c3c",
    "Manual Review Required": "#f39c12",
    "Explained Variation": "#2ecc71",
    "Insufficient Evidence": "#95a5a6",
}


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Multi-Factor Disparity Detection & Evidence Analysis")
    st.markdown("Identifies unexplained compensation disparities benchmarked against peer cohort medians, documented performance ratings, and tenure.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)
    curr_norm = get_currency_normalizer(db)

    status_filter = st.selectbox(
        "Filter by Disparity Outcome Status:",
        ["All Outcomes", "Unexplained Disparity", "Manual Review Required", "Explained Variation", "Insufficient Evidence"],
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
        if band:
            b_min, b_mid, b_max = get_band_usd_amounts(band, curr_norm)
        else:
            b_min, b_mid, b_max = med_sal * 0.8, med_sal, med_sal * 1.2

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
            "Salary (USD)": float(sal.normalized_salary),
            "Cohort Median": float(med_sal),
            "Deviation (%)": float(res.deviation_from_cohort_median_pct),
            "Compa-Ratio": float(res.compa_ratio),
            "Rating": float(rating) if rating is not None else None,
            "Company Tenure (yrs)": float(c_tenure),
            "Status": _STATUS_LABELS.get(res.status, res.status),
            "Primary Reason": res.primary_reason,
            "Is Disparity": bool(res.is_disparity),
        })

    df = pd.DataFrame(findings)
    if df.empty:
        st.info("No employee records available for disparity evaluation.")
        return

    unexplained_count = len(df[df["Status"] == "Unexplained Disparity"])
    review_count = len(df[df["Status"] == "Manual Review Required"])
    explained_count = len(df[df["Status"] == "Explained Variation"])
    insufficient_count = len(df[df["Status"] == "Insufficient Evidence"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unexplained Disparities", f"{unexplained_count:,}", delta=f"{unexplained_count} flagged", delta_color="inverse")
    col2.metric("Manual Review Required", f"{review_count:,}", "Mixed signals detected")
    col3.metric("Explained Variations", f"{explained_count:,}", "Supported by merit or tenure")
    col4.metric("Insufficient Evidence", f"{insufficient_count:,}", "Cohort too small to conclude")

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
            color_discrete_map=_STATUS_COLORS,
        )
        apply_clean_layout(fig_pie, legend_bottom=True, height=450)
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_scatter:
        # Focus scatter y-axis around realistic deviation window [-80%, +150%] so outliers don't flatten the chart
        df_scatter = df[(df["Deviation (%)"] >= -80.0) & (df["Deviation (%)"] <= 150.0)].copy()
        fig_disp = px.scatter(
            df_scatter,
            x="Rating",
            y="Deviation (%)",
            color="Status",
            hover_data=["Employee ID", "Name", "Salary (USD)"],
            title="Performance Rating vs Cohort Deviation (%)",
            color_discrete_map=_STATUS_COLORS,
        )
        fig_disp.add_hline(
            y=-15.0, line_dash="dash", line_color="#e74c3c",
            annotation_text="Disparity Threshold (-15%)", annotation_position="bottom right"
        )
        fig_disp.add_vline(
            x=3.5, line_dash="dash", line_color="#3498db",
            annotation_text="High Performer (3.5+)", annotation_position="top right"
        )
        apply_clean_layout(fig_disp, legend_bottom=True, height=450)
        st.plotly_chart(fig_disp, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Disparity Evaluation Findings")
    filtered_df = df if status_filter == "All Outcomes" else df[df["Status"] == status_filter]
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Salary (USD)": st.column_config.NumberColumn("Salary (USD)", format="$%,.0f"),
            "Cohort Median": st.column_config.NumberColumn("Cohort Median", format="$%,.0f"),
            "Deviation (%)": st.column_config.NumberColumn("Deviation (%)", format="%.1f%%"),
            "Compa-Ratio": st.column_config.NumberColumn("Compa-Ratio", format="%.2f"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.2f"),
            "Company Tenure (yrs)": st.column_config.NumberColumn("Tenure (yrs)", format="%.1f"),
        },
    )
