"""
View 1: Executive Overview Dashboard.
Displays high-level KPIs, metric scorecards, and high-impact visual distributions.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand, AdjustmentProposal
from src.dashboard.views.helpers import get_role_map, get_level_map, get_location_map, map_col, PLOTLY_CONFIG


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Overview & Equity Scorecard")
    st.markdown("High-level visibility into enterprise compensation structure, detected disparities, and remediation proposals.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    # KPIs
    total_employees = db.query(Employee).count()
    total_salary_records = db.query(SalaryRecord).count()
    total_proposals = db.query(AdjustmentProposal).count()
    pending_proposals = db.query(AdjustmentProposal).filter_by(approval_status="PENDING_REVIEW").count()
    approved_proposals = db.query(AdjustmentProposal).filter_by(approval_status="APPROVED").count()
    rejected_proposals = db.query(AdjustmentProposal).filter_by(approval_status="REJECTED").count()

    # Latest 2026 salaries
    salaries = db.query(
        Employee.employee_id,
        Employee.department,
        Employee.current_location_id,
        Employee.current_role_id,
        Employee.current_level_id,
        SalaryRecord.normalized_salary
    ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
        SalaryRecord.effective_date >= "2026-01-01"
    ).all()

    df_sal = pd.DataFrame(salaries, columns=["employee_id", "department", "location_id", "role_id", "level_id", "normalized_salary"])

    if selected_role != "All":
        df_sal = df_sal[df_sal["role_id"] == selected_role]
    if selected_level != "All":
        df_sal = df_sal[df_sal["level_id"] == selected_level]
    if selected_location != "All":
        df_sal = df_sal[df_sal["location_id"] == selected_location]

    avg_salary = df_sal["normalized_salary"].mean() if not df_sal.empty else 0.0
    median_salary = df_sal["normalized_salary"].median() if not df_sal.empty else 0.0

    # KPI Metric Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Workforce", f"{total_employees:,}")
    col2.metric("Salary Records", f"{total_salary_records:,}")
    col3.metric("Avg Annual Salary", f"${avg_salary:,.0f}")
    col4.metric("Median Salary", f"${median_salary:,.0f}")
    col5.metric("Active Proposals", f"{total_proposals}", f"{pending_proposals} pending")

    st.markdown("---")

    # Resolve IDs to names for display
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
            fig_dept.update_layout(showlegend=False)
            st.plotly_chart(fig_dept, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No records match the current filter selection.")

    with col_chart2:
        st.subheader("Adjustment Proposals by Lifecycle Status")
        proposal_counts = {
            "Pending Review": pending_proposals,
            "Approved": approved_proposals,
            "Rejected": rejected_proposals,
            "Draft": total_proposals - (pending_proposals + approved_proposals + rejected_proposals)
        }
        df_props = pd.DataFrame(list(proposal_counts.items()), columns=["Status", "Count"])
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
        st.plotly_chart(fig_donut, use_container_width=True, config=PLOTLY_CONFIG)

    # Location Spend — use full names
    st.subheader("Location Benchmarks & Workforce Distribution")
    if not df_sal.empty:
        loc_summary = df_sal.groupby("Location").agg(
            headcount=("employee_id", "count"),
            avg_salary=("normalized_salary", "mean"),
            median_salary=("normalized_salary", "median")
        ).reset_index()

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
        fig_bar.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)
