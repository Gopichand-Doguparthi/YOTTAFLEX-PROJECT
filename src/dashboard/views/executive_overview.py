"""
View 1: Executive Overview Dashboard.
Displays enterprise-wide totals, a dedicated filtered-selection KPI section,
and interactive compensation & proposal distributions.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, AdjustmentProposal
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    PLOTLY_CONFIG, apply_clean_layout,
)


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Overview & Equity Scorecard")
    st.markdown("High-level visibility into enterprise compensation structure, detected disparities, and remediation proposals.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    # ── 1. Enterprise-Wide Unfiltered Totals ──
    total_employees = db.query(Employee).count()
    total_salary_records = db.query(SalaryRecord).count()
    total_proposals = db.query(AdjustmentProposal).count()
    pending_proposals = db.query(AdjustmentProposal).filter_by(approval_status="PENDING_REVIEW").count()
    approved_proposals = db.query(AdjustmentProposal).filter_by(approval_status="APPROVED").count()
    rejected_proposals = db.query(AdjustmentProposal).filter_by(approval_status="REJECTED").count()

    st.subheader("Enterprise-Wide Totals (All Workforce)")
    e_col1, e_col2, e_col3, e_col4 = st.columns(4)
    e_col1.metric("Enterprise Workforce", f"{total_employees:,}")
    e_col2.metric("Total Salary Records", f"{total_salary_records:,}")
    e_col3.metric("Total Proposals", f"{total_proposals:,}")
    e_col4.metric("Pending Review Proposals", f"{pending_proposals:,}")

    st.markdown("---")

    # ── 2. Filtered Selection Metrics ──
    emp_query = db.query(Employee.employee_id)
    if selected_role != "All":
        emp_query = emp_query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        emp_query = emp_query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        emp_query = emp_query.filter(Employee.current_location_id == selected_location)

    filtered_emp_ids = [r[0] for r in emp_query.all()]
    filtered_workforce = len(filtered_emp_ids)

    if filtered_emp_ids:
        filtered_sal_count = db.query(SalaryRecord).filter(
            SalaryRecord.employee_id.in_(filtered_emp_ids)
        ).count()
        filtered_prop_total = db.query(AdjustmentProposal).filter(
            AdjustmentProposal.employee_id.in_(filtered_emp_ids)
        ).count()
        filtered_prop_pending = db.query(AdjustmentProposal).filter(
            AdjustmentProposal.employee_id.in_(filtered_emp_ids),
            AdjustmentProposal.approval_status == "PENDING_REVIEW"
        ).count()
        filtered_prop_approved = db.query(AdjustmentProposal).filter(
            AdjustmentProposal.employee_id.in_(filtered_emp_ids),
            AdjustmentProposal.approval_status == "APPROVED"
        ).count()
        filtered_prop_rejected = db.query(AdjustmentProposal).filter(
            AdjustmentProposal.employee_id.in_(filtered_emp_ids),
            AdjustmentProposal.approval_status == "REJECTED"
        ).count()
    else:
        filtered_sal_count = 0
        filtered_prop_total = 0
        filtered_prop_pending = 0
        filtered_prop_approved = 0
        filtered_prop_rejected = 0

    # Latest 2026 salaries for filtered scope
    salaries_q = db.query(
        Employee.employee_id,
        Employee.department,
        Employee.current_location_id,
        Employee.current_role_id,
        Employee.current_level_id,
        SalaryRecord.normalized_salary
    ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
        SalaryRecord.effective_date >= "2026-01-01"
    )
    if selected_role != "All":
        salaries_q = salaries_q.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        salaries_q = salaries_q.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        salaries_q = salaries_q.filter(Employee.current_location_id == selected_location)

    df_sal = pd.DataFrame(
        salaries_q.all(),
        columns=["employee_id", "department", "location_id", "role_id", "level_id", "normalized_salary"]
    )

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

    # Resolve IDs to full names
    if not df_sal.empty:
        df_sal["Location"] = df_sal["location_id"].map(lambda x: loc_map.get(x, x))
        df_sal["Role"] = df_sal["role_id"].map(lambda x: role_map.get(x, x))

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Salary Distribution by Department")
        if not df_sal.empty:
            fig_dept = px.box(
                df_sal,
                x="department",
                y="normalized_salary",
                color="department",
                points="outliers",
                labels={"normalized_salary": "Normalized Salary (USD)", "department": "Department"},
                title="Normalized Compensation Spread by Department"
            )
            apply_clean_layout(fig_dept, legend_bottom=False, height=440, xaxis_tickangle=-25)
            fig_dept.update_layout(showlegend=False)
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
                    "Pending Review": "#f39c12",
                    "Approved": "#27ae60",
                    "Rejected": "#e74c3c",
                    "Draft": "#7f8c8d"
                },
                title="Remediation Proposal Status Breakdown"
            )
            apply_clean_layout(fig_donut, legend_bottom=True, height=440)
            st.plotly_chart(fig_donut, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No proposals found for the active filter selection.")

    # Location Spend — full city names, clean colorbar placement
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
        fig_bar.update_traces(textposition="outside", cliponaxis=False)
        apply_clean_layout(fig_bar, legend_bottom=False, height=480, xaxis_tickangle=-30, extra_bottom_margin=20)
        fig_bar.update_layout(
            coloraxis_colorbar=dict(
                title="Avg Salary (USD)",
                y=0.45,
                len=0.75,
                yanchor="middle",
            )
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)
