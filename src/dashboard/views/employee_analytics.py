"""
View 2: Employee and Salary Analytics.
Provides directory exploration, compensation progression tracking, and profile drill-downs.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, PerformanceEvidence, Tenure, Promotion


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Employee & Salary History Analytics")
    st.markdown("Detailed breakdown of workforce demographics, historical compensation events, and individual employee progression.")

    # Search & Filters
    search_query = st.text_input("Search by Employee ID, Name, or Email:", "")

    query = db.query(Employee)
    if selected_role != "All":
        query = query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        query = query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        query = query.filter(Employee.current_location_id == selected_location)

    employees = query.limit(500).all()

    if not employees:
        st.warning("No employees found matching the specified filters.")
        return

    # Data Table
    emp_data = []
    for e in employees:
        if search_query:
            term = search_query.lower()
            if not (term in e.employee_id.lower() or term in e.first_name.lower() or term in e.last_name.lower() or term in e.email.lower()):
                continue

        emp_data.append({
            "Employee ID": e.employee_id,
            "Name": f"{e.first_name} {e.last_name}",
            "Department": e.department,
            "Role": e.current_role_id,
            "Level": e.current_level_id,
            "Location": e.current_location_id,
            "Type": e.employment_type,
            "FTE": e.fte,
            "Hire Date": str(e.hire_date)
        })

    df_emps = pd.DataFrame(emp_data)
    st.dataframe(df_emps, use_container_width=True, height=280)

    # Detailed Employee Drill-down
    st.markdown("---")
    st.subheader("Employee Profile & Career Trajectory Drill-Down")
    selected_emp_id = st.selectbox(
        "Select an Employee to view comprehensive history:",
        df_emps["Employee ID"].tolist() if not df_emps.empty else []
    )

    if selected_emp_id:
        emp = db.query(Employee).filter(Employee.employee_id == selected_emp_id).first()
        salaries = db.query(SalaryRecord).filter(SalaryRecord.employee_id == selected_emp_id).order_by(SalaryRecord.effective_date.asc()).all()
        perfs = db.query(PerformanceEvidence).filter(PerformanceEvidence.employee_id == selected_emp_id).order_by(PerformanceEvidence.effective_date.asc()).all()
        proms = db.query(Promotion).filter(Promotion.employee_id == selected_emp_id).all()
        tenure = db.query(Tenure).filter(Tenure.employee_id == selected_emp_id).first()

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Employee:** {emp.first_name} {emp.last_name}")
            st.markdown(f"**Email:** `{emp.email}`")
            st.markdown(f"**Department:** {emp.department}")
        with col_b:
            st.markdown(f"**Role:** `{emp.current_role_id}`")
            st.markdown(f"**Level:** `{emp.current_level_id}`")
            st.markdown(f"**Location:** `{emp.current_location_id}`")
        with col_c:
            st.markdown(f"**Hire Date:** {emp.hire_date}")
            st.markdown(f"**FTE:** {emp.fte} ({emp.employment_type})")
            if tenure:
                st.markdown(f"**Company Tenure:** {tenure.tenure_in_company_years} yrs (Total: {tenure.years_of_experience_total} yrs)")

        # Salary Trajectory Chart
        if salaries:
            sal_df = pd.DataFrame([
                {
                    "Effective Date": str(s.effective_date),
                    "Normalized Salary (USD)": s.normalized_salary,
                    "Base Salary": s.base_salary,
                    "Currency": s.currency,
                    "Change Reason": s.change_reason
                }
                for s in salaries
            ])

            fig_traj = px.line(
                sal_df,
                x="Effective Date",
                y="Normalized Salary (USD)",
                markers=True,
                text="Normalized Salary (USD)",
                title=f"Compensation Trajectory: {emp.first_name} {emp.last_name} ({emp.employee_id})"
            )
            fig_traj.update_traces(textposition="top center")
            st.plotly_chart(fig_traj, use_container_width=True)

            st.write("Historical Compensation Records:")
            st.dataframe(sal_df, use_container_width=True)

        if perfs:
            st.write("Performance Evaluation Reviews:")
            perf_df = pd.DataFrame([
                {
                    "Review Cycle": p.review_cycle,
                    "Rating Score": p.rating_score,
                    "Rating Label": p.rating_label,
                    "Skills Score": p.documented_skills_score,
                    "Critical Initiatives": p.critical_initiative_count,
                    "Review Date": str(p.effective_date)
                }
                for p in perfs
            ])
            st.dataframe(perf_df, use_container_width=True)
