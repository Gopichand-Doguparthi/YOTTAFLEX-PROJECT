"""
View 7: Comparable Employee Groups.
Analyzes cohort segmentation, peer group sizes, and documented role comparability rationales.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, RoleComparabilityRationale
from src.engine.comparable_groups import ComparableGroupEngine
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    fmt_usd, PLOTLY_CONFIG, apply_clean_layout, build_table_column_config,
)


@st.cache_data(ttl=120, show_spinner=False)
def _load_cohort_and_rationales():
    db = SessionLocal()
    try:
        rows = db.query(
            Employee.employee_id,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
            SalaryRecord.normalized_salary
        ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
            SalaryRecord.effective_date >= "2026-01-01"
        ).all()
        records = [
            {
                "employee_id": r[0],
                "role_id": r[1],
                "level_id": r[2],
                "location_id": r[3],
                "normalized_salary": float(r[4]),
            }
            for r in rows
        ]
        rationales = [
            {
                "mapping_id": r.mapping_id,
                "role_id_a": r.role_id_a,
                "role_id_b": r.role_id_b,
                "is_comparable": bool(r.is_comparable),
                "documented_rationale": r.documented_rationale,
                "approved_by": r.approved_by,
                "effective_date": str(r.effective_date),
            }
            for r in db.query(RoleComparabilityRationale).all()
        ]
        return records, rationales
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Comparable Employee Groups & Peer Cohort Analysis")
    st.markdown("Audits peer cohort formation across role, level, and location, verifying statistical sufficiency and cross-role bridge rationales.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    all_records, rationales = _load_cohort_and_rationales()

    records = [
        r for r in all_records
        if (selected_role == "All" or r["role_id"] == selected_role)
        and (selected_level == "All" or r["level_id"] == selected_level)
        and (selected_location == "All" or r["location_id"] == selected_location)
    ]

    group_engine = ComparableGroupEngine(rationales=rationales)
    stats = group_engine.compute_cohort_statistics(records, min_cohort_size=3)

    if not stats:
        st.info("No cohorts found matching selected filters.")
        return

    raw_df = pd.DataFrame(list(stats.values()))

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
        "Median Salary (USD)": raw_df["median_salary"].map(fmt_usd),
        "Mean Salary (USD)": raw_df["mean_salary"].map(fmt_usd),
        "Min Salary (USD)": raw_df["min_salary"].map(fmt_usd),
        "Max Salary (USD)": raw_df["max_salary"].map(fmt_usd),
        "Std Dev (USD)": raw_df["std_salary"].map(fmt_usd),
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
        text_auto=True,
        labels={"Members": "Cohort Member Count", "Status": "Statistical Sufficiency"},
        title="Distribution of Cohort Member Sizes",
        color_discrete_map={
            "Sufficient (N >= 3)": "#22c55e",
            "Insufficient (N < 3)": "#ef4444",
        },
    )
    fig_hist.add_vline(
        x=3, line_dash="dash", line_color="#e74c3c",
        annotation_text="Minimum Threshold (N=3)", annotation_position="top right", annotation_yshift=-6
    )
    apply_clean_layout(fig_hist, legend_bottom=True, height=440)
    st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Peer Cohort Benchmarks & Metrics")
    cg_status_filter = st.selectbox(
        "Filter by Statistical Sufficiency:",
        ["All Cohorts", "Sufficient (N >= 3)", "Insufficient (N < 3)"],
        index=0,
    )
    cohort_disp_df = cohort_df.drop(columns=["is_sufficient"])
    if cg_status_filter != "All Cohorts":
        cohort_disp_df = cohort_disp_df[cohort_disp_df["Status"] == cg_status_filter]
    st.caption(f"Showing {len(cohort_disp_df):,} cohort(s)")
    st.dataframe(
        cohort_disp_df,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(cohort_disp_df),
    )

    st.markdown("---")
    st.subheader("Approved Cross-Role Comparability Rationales")
    rat_comp_filter = st.selectbox("Filter by Comparability:", ["All", "Yes", "No"], index=0)
    rat_df = pd.DataFrame([
        {
            "Mapping ID": r["mapping_id"],
            "Role A": role_map.get(r["role_id_a"], r["role_id_a"]),
            "Role B": role_map.get(r["role_id_b"], r["role_id_b"]),
            "Comparable": "Yes" if r["is_comparable"] else "No",
            "Documented Rationale": r["documented_rationale"],
            "Approved By": r["approved_by"],
            "Effective Date": r["effective_date"]
        }
        for r in rationales
    ])
    if rat_comp_filter != "All":
        rat_df = rat_df[rat_df["Comparable"] == rat_comp_filter]
    st.dataframe(
        rat_df,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(rat_df),
    )
