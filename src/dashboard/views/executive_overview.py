"""
View 1: Executive Overview Dashboard.
Displays enterprise-wide totals, a dedicated filtered-selection KPI section,
and bar/donut visualizations.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, AdjustmentProposal
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    PLOTLY_CONFIG, apply_clean_layout,
)


@st.cache_data(ttl=120, show_spinner=False)
def _load_overview_data():
    """Fetches lightweight tuples once and caches them for fast tab switching."""
    db = SessionLocal()
    try:
        total_employees = db.query(Employee).count()
        total_salary_records = db.query(SalaryRecord).count()

        salaries_2026 = db.query(
            Employee.employee_id,
            Employee.department,
            Employee.current_location_id,
            Employee.current_role_id,
            Employee.current_level_id,
            SalaryRecord.normalized_salary,
        ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
            SalaryRecord.effective_date >= "2026-01-01"
        ).all()

        sal_counts_by_emp = dict(
            db.query(
                SalaryRecord.employee_id,
                __import__("sqlalchemy").func.count(SalaryRecord.salary_id),
            ).group_by(SalaryRecord.employee_id).all()
        )

        emp_rows = db.query(
            Employee.employee_id,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
        ).all()

        prop_rows = db.query(
            AdjustmentProposal.employee_id,
            AdjustmentProposal.approval_status,
        ).all()

        return {
            "total_employees": total_employees,
            "total_salary_records": total_salary_records,
            "salaries_2026": [tuple(r) for r in salaries_2026],
            "sal_counts_by_emp": sal_counts_by_emp,
            "emp_rows": [tuple(r) for r in emp_rows],
            "prop_rows": [tuple(r) for r in prop_rows],
        }
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Overview & Equity Scorecard")
    st.markdown("High-level visibility into enterprise compensation structure, detected disparities, and remediation proposals.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    snap = _load_overview_data()

    # 1. Enterprise-Wide Unfiltered Totals
    all_props = snap["prop_rows"]
    total_proposals = len(all_props)
    pending_proposals = sum(1 for _, st_val in all_props if st_val == "PENDING_REVIEW")

    st.subheader("Enterprise-Wide Totals (All Workforce)")
    e_col1, e_col2, e_col3, e_col4 = st.columns(4)
    e_col1.metric("Enterprise Workforce", f"{snap['total_employees']:,}")
    e_col2.metric("Total Salary Records", f"{snap['total_salary_records']:,}")
    e_col3.metric("Total Proposals", f"{total_proposals:,}")
    e_col4.metric("Pending Review Proposals", f"{pending_proposals:,}")

    st.markdown("---")

    # 2. Filtered Selection Metrics
    filtered_emp_ids = {
        eid
        for eid, rid, lid, loc_id in snap["emp_rows"]
        if (selected_role == "All" or rid == selected_role)
        and (selected_level == "All" or lid == selected_level)
        and (selected_location == "All" or loc_id == selected_location)
    }

    filtered_workforce = len(filtered_emp_ids)
    sal_counts_by_emp = snap["sal_counts_by_emp"]
    filtered_sal_count = sum(sal_counts_by_emp.get(eid, 0) for eid in filtered_emp_ids)

    filtered_props = [st_val for eid, st_val in all_props if eid in filtered_emp_ids]
    filtered_prop_total = len(filtered_props)
    filtered_prop_pending = sum(1 for s in filtered_props if s == "PENDING_REVIEW")
    filtered_prop_approved = sum(1 for s in filtered_props if s == "APPROVED")
    filtered_prop_rejected = sum(1 for s in filtered_props if s == "REJECTED")

    df_sal = pd.DataFrame(
        snap["salaries_2026"],
        columns=["employee_id", "department", "location_id", "role_id", "level_id", "normalized_salary"],
    )
    if selected_role != "All":
        df_sal = df_sal[df_sal["role_id"] == selected_role]
    if selected_level != "All":
        df_sal = df_sal[df_sal["level_id"] == selected_level]
    if selected_location != "All":
        df_sal = df_sal[df_sal["location_id"] == selected_location]

    avg_salary = df_sal["normalized_salary"].mean() if not df_sal.empty else 0.0
    median_salary = df_sal["normalized_salary"].median() if not df_sal.empty else 0.0

    filter_parts = [
        f"Role: **{role_map.get(selected_role, selected_role)}**" if selected_role != "All" else "Role: **All**",
        f"Level: **{level_map.get(selected_level, selected_level)}**" if selected_level != "All" else "Level: **All**",
        f"Location: **{loc_map.get(selected_location, selected_location)}**" if selected_location != "All" else "Location: **All**",
    ]
    st.subheader("Filtered Selection Metrics")
    st.caption("Active Scope — " + "  |  ".join(filter_parts))

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Filtered Workforce", f"{filtered_workforce:,}")
    col2.metric("Filtered Salary Records", f"{filtered_sal_count:,}")
    col3.metric("Avg Annual Salary", f"${avg_salary:,.0f}")
    col4.metric("Median Salary", f"${median_salary:,.0f}")
    col5.metric("Filtered Proposals", f"{filtered_prop_total:,}", f"{filtered_prop_pending} pending")

    st.markdown("---")

    if not df_sal.empty:
        df_sal = df_sal.copy()
        df_sal["Location"] = df_sal["location_id"].map(lambda x: loc_map.get(x, x))

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Salary Benchmarks by Department")
        if not df_sal.empty:
            dept_summary = (
                df_sal.groupby("department")["normalized_salary"]
                .agg(Average="mean", Median="median")
                .reset_index()
                .melt(id_vars="department", value_vars=["Average", "Median"], var_name="Metric", value_name="Salary (USD)")
            )
            max_dept_val = float(dept_summary["Salary (USD)"].max()) if not dept_summary.empty else 100000.0
            dept_summary["Label"] = dept_summary["Salary (USD)"].map(lambda v: f"${v/1000:,.0f}k")
            fig_dept = px.bar(
                dept_summary,
                x="department",
                y="Salary (USD)",
                color="Metric",
                barmode="group",
                text="Label",
                labels={"department": "Department", "Salary (USD)": "Normalized Salary (USD)"},
                title="Average vs. Median Annual Salary by Department",
                color_discrete_map={"Average": "#6366f1", "Median": "#22c55e"},
            )
            fig_dept.update_traces(
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{x}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>",
            )
            fig_dept.update_layout(yaxis=dict(range=[0, max_dept_val * 1.20]))
            apply_clean_layout(fig_dept, legend_bottom=True, height=450, xaxis_tickangle=-25)
            st.plotly_chart(fig_dept, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No records match the current filter selection.")

    with col_chart2:
        st.subheader("Adjustment Proposals by Lifecycle Status")
        proposal_counts = {
            "Pending Review": filtered_prop_pending,
            "Approved": filtered_prop_approved,
            "Rejected": filtered_prop_rejected,
            "Draft": max(0, filtered_prop_total - (filtered_prop_pending + filtered_prop_approved + filtered_prop_rejected)),
        }
        df_props = pd.DataFrame(list(proposal_counts.items()), columns=["Status", "Count"])
        if df_props["Count"].sum() > 0:
            fig_donut = px.pie(
                df_props,
                names="Status",
                values="Count",
                hole=0.45,
                color="Status",
                color_discrete_map={
                    "Pending Review": "#f59e0b",
                    "Approved": "#10b981",
                    "Rejected": "#ef4444",
                    "Draft": "#3b82f6",
                },
                title="Remediation Proposal Status Breakdown"
            )
            fig_donut.update_traces(
                textinfo="percent+value",
                marker=dict(line=dict(color="#0f172a", width=2)),
            )
            apply_clean_layout(fig_donut, legend_bottom=True, height=450, legend_position="bottom")
            st.plotly_chart(fig_donut, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No proposals found for the active filter selection.")

    st.subheader("Location Benchmarks & Workforce Distribution")
    if not df_sal.empty:
        loc_summary = df_sal.groupby("Location").agg(
            headcount=("employee_id", "count"),
            avg_salary=("normalized_salary", "mean"),
            median_salary=("normalized_salary", "median")
        ).reset_index().sort_values("headcount", ascending=False)

        fig_bar = px.bar(
            loc_summary,
            x="Location",
            y="headcount",
            color="avg_salary",
            text="headcount",
            labels={"Location": "City", "headcount": "Employee Count", "avg_salary": "Avg Salary (USD)"},
            title="Workforce Count and Average Normalized Salary by Geographic Hub",
            color_continuous_scale="Viridis"
        )
        max_hc = int(loc_summary["headcount"].max()) if not loc_summary.empty else 100
        fig_bar.update_traces(textposition="outside", cliponaxis=False)
        fig_bar.update_layout(yaxis=dict(range=[0, max_hc * 1.16]))
        apply_clean_layout(fig_bar, legend_bottom=False, height=500, xaxis_tickangle=-30, extra_bottom_margin=20)
        fig_bar.update_layout(
            coloraxis_colorbar=dict(
                title="Avg Salary (USD)",
                y=0.45,
                len=0.72,
                yanchor="middle",
            )
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)
