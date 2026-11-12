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
from src.dashboard.views.helpers import get_role_map, get_level_map, get_location_map, PLOTLY_CONFIG


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

    cohort_df = pd.DataFrame(list(stats.values()))

    # Resolve IDs in cohort_df if present
    for id_col, name_col, lkp in [
        ("role_id", "Role", role_map),
        ("level_id", "Level", level_map),
        ("location_id", "Location", loc_map),
    ]:
        if id_col in cohort_df.columns:
            cohort_df[name_col] = cohort_df[id_col].map(lambda x: lkp.get(x, x))

    total_cohorts = len(cohort_df)
    sufficient_cohorts = len(cohort_df[cohort_df["is_sufficient"]])
    insufficient_cohorts = total_cohorts - sufficient_cohorts

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Peer Cohorts", total_cohorts)
    col2.metric("Statistically Sufficient (N >= 3)", sufficient_cohorts)
    col3.metric("Insufficient Evidence (N < 3)", insufficient_cohorts, delta=f"{insufficient_cohorts} cohorts", delta_color="inverse")

    st.markdown("---")

    st.subheader("Peer Cohort Size Distribution")
    fig_hist = px.histogram(
        cohort_df,
        x="count",
        color="status",
        nbins=20,
        labels={"count": "Cohort Member Count", "status": "Statistical Sufficiency"},
        title="Distribution of Cohort Member Sizes"
    )
    fig_hist.add_vline(x=3, line_dash="dash", line_color="red", annotation_text="Minimum Threshold (N=3)")
    st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Peer Cohort Benchmarks & Metrics")
    st.dataframe(cohort_df, use_container_width=True)

    st.markdown("---")
    st.subheader("Approved Cross-Role Comparability Rationales")
    rationales = db.query(RoleComparabilityRationale).all()
    rat_df = pd.DataFrame([
        {
            "Mapping ID": r.mapping_id,
            "Role A": role_map.get(r.role_id_a, r.role_id_a),
            "Role B": role_map.get(r.role_id_b, r.role_id_b),
            "Is Comparable": r.is_comparable,
            "Documented Rationale": r.documented_rationale,
            "Approved By": r.approved_by,
            "Effective Date": str(r.effective_date)
        }
        for r in rationales
    ])
    st.dataframe(rat_df, use_container_width=True)
