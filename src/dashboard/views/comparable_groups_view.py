"""
View 7: Comparable Employee Groups.
Analyzes cohort segmentation, peer group sizes, and documented role comparability rationales.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, RoleComparabilityRationale
from src.engine.comparable_groups import ComparableGroupEngine
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    PLOTLY_CONFIG, apply_clean_layout,
)


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Comparable Employee Groups & Peer Cohort Analysis")
    st.markdown("Audits peer cohort formation across role, level, and location, verifying statistical sufficiency and cross-role bridge rationales.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    group_engine = ComparableGroupEngine()
    group_engine.load_rationales_from_db(db)

    query = db.query(
        Employee.employee_id,
        Employee.current_role_id,
        Employee.current_level_id,
        Employee.current_location_id,
        SalaryRecord.normalized_salary
    ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
        SalaryRecord.effective_date >= "2026-01-01"
    )

    if selected_role != "All":
        query = query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        query = query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        query = query.filter(Employee.current_location_id == selected_location)

    records = [
        {
            "employee_id": r[0],
            "role_id": r[1],
            "level_id": r[2],
            "location_id": r[3],
            "normalized_salary": r[4]
        }
        for r in query.all()
    ]

    stats = group_engine.compute_cohort_statistics(records, min_cohort_size=3)

    if not stats:
        st.info("No cohorts found matching selected filters.")
        return

    raw_df = pd.DataFrame(list(stats.values()))

    # Parse cohort_key into human-readable Role, Level, Location
    roles_col, levels_col, locs_col = [], [], []
    for k in raw_df["cohort_key"]:
        parts = str(k).split("::")
        r_id = parts[0] if len(parts) > 0 else ""
        l_id = parts[1] if len(parts) > 1 else ""
        loc_id = parts[2] if len(parts) > 2 else ""
        roles_col.append(role_map.get(r_id, r_id))
        levels_col.append(level_map.get(l_id, l_id))
        locs_col.append(loc_map.get(loc_id, loc_id))

    cohort_df = pd.DataFrame({
        "Role": roles_col,
        "Level": levels_col,
        "Location": locs_col,
        "Members": raw_df["count"],
        "Median Salary (USD)": raw_df["median_salary"],
        "Mean Salary (USD)": raw_df["mean_salary"],
        "Min Salary (USD)": raw_df["min_salary"],
        "Max Salary (USD)": raw_df["max_salary"],
        "Std Dev (USD)": raw_df["std_salary"],
        "Status": raw_df["status"].map({"SUFFICIENT": "Sufficient (N >= 3)", "INSUFFICIENT_EVIDENCE": "Insufficient (N < 3)"}).fillna(raw_df["status"]),
        "is_sufficient": raw_df["is_sufficient"],
    })

    total_cohorts = len(cohort_df)
    sufficient_cohorts = int(cohort_df["is_sufficient"].sum())
    insufficient_cohorts = total_cohorts - sufficient_cohorts

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Peer Cohorts", f"{total_cohorts:,}")
    col2.metric("Statistically Sufficient (N >= 3)", f"{sufficient_cohorts:,}")
    col3.metric("Insufficient Evidence (N < 3)", f"{insufficient_cohorts:,}", delta=f"{insufficient_cohorts} cohorts", delta_color="inverse")

    st.markdown("---")

    st.subheader("Peer Cohort Size Distribution")
    fig_hist = px.histogram(
        cohort_df,
        x="Members",
        color="Status",
        nbins=20,
        labels={"Members": "Cohort Member Count", "Status": "Statistical Sufficiency"},
        title="Distribution of Cohort Member Sizes",
        color_discrete_map={
            "Sufficient (N >= 3)": "#2ecc71",
            "Insufficient (N < 3)": "#e74c3c",
        },
    )
    fig_hist.add_vline(
        x=3, line_dash="dash", line_color="#e74c3c",
        annotation_text="Minimum Threshold (N=3)", annotation_position="top right"
    )
    apply_clean_layout(fig_hist, legend_bottom=True, height=430)
    st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Peer Cohort Benchmarks & Metrics")
    display_cohort_df = cohort_df.drop(columns=["is_sufficient"])
    st.dataframe(
        display_cohort_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Median Salary (USD)": st.column_config.NumberColumn("Median Salary", format="$%,.0f"),
            "Mean Salary (USD)": st.column_config.NumberColumn("Mean Salary", format="$%,.0f"),
            "Min Salary (USD)": st.column_config.NumberColumn("Min Salary", format="$%,.0f"),
            "Max Salary (USD)": st.column_config.NumberColumn("Max Salary", format="$%,.0f"),
            "Std Dev (USD)": st.column_config.NumberColumn("Std Dev", format="$%,.0f"),
        },
    )

    st.markdown("---")
    st.subheader("Approved Cross-Role Comparability Rationales")
    rationales = db.query(RoleComparabilityRationale).all()
    rat_df = pd.DataFrame([
        {
            "Mapping ID": r.mapping_id,
            "Role A": role_map.get(r.role_id_a, r.role_id_a),
            "Role B": role_map.get(r.role_id_b, r.role_id_b),
            "Comparable": "Yes" if r.is_comparable else "No",
            "Documented Rationale": r.documented_rationale,
            "Approved By": r.approved_by,
            "Effective Date": str(r.effective_date)
        }
        for r in rationales
    ])
    st.dataframe(rat_df, use_container_width=True, hide_index=True)
