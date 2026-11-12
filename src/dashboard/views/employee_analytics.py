"""
View 2: Employee and Salary Analytics.
Provides directory exploration, compensation progression tracking, and profile drill-downs.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, PerformanceEvidence, Tenure, Promotion
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    PLOTLY_CONFIG, apply_clean_layout,
)


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Employee & Salary History Analytics")
    st.markdown("Detailed breakdown of workforce demographics, historical compensation events, and individual employee progression.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    # Search & Filters
    search_query = st.text_input("Search by Employee ID, Name, or Email:", "")

    query = db.query(Employee)
    if selected_role != "All":
        query = query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        query = query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        query = query.filter(Employee.current_location_id == selected_location)

    employees = query.all()

    if not employees:
        st.warning("No employees found matching the specified filters.")
        return

    emp_data = []
    for e in employees:
        if search_query:
            term = search_query.lower()
            if not (term in e.employee_id.lower() or term in e.first_name.lower()
                    or term in e.last_name.lower() or term in e.email.lower()):
                continue

        emp_data.append({
            "Employee ID": e.employee_id,
            "Name": f"{e.first_name} {e.last_name}",
            "Department": e.department,
            "Role": role_map.get(e.current_role_id, e.current_role_id),
            "Level": level_map.get(e.current_level_id, e.current_level_id),
            "Location": loc_map.get(e.current_location_id, e.current_location_id),
            "Type": e.employment_type.replace("_", " ").title(),
            "FTE": float(e.fte),
            "Hire Date": str(e.hire_date)
        })

    df_emps = pd.DataFrame(emp_data)
    st.caption(f"Showing {len(df_emps):,} employee records")
    st.dataframe(
        df_emps,
        use_container_width=True,
        height=320,
        hide_index=True,
        column_config={
            "FTE": st.column_config.NumberColumn("FTE", format="%.2f"),
        },
    )

    # Detailed Employee Drill-down
    st.markdown("---")
    st.subheader("Employee Profile & Career Trajectory Drill-Down")
    if df_emps.empty:
        st.info("No employees match your search query.")
        return

    emp_options = [f"{row['Name']} ({row['Employee ID']})" for _, row in df_emps.iterrows()]
    emp_id_lookup = {f"{row['Name']} ({row['Employee ID']})": row["Employee ID"] for _, row in df_emps.iterrows()}
    selected_label = st.selectbox("Select an Employee to view comprehensive history:", emp_options)
    selected_emp_id = emp_id_lookup[selected_label]

    if selected_emp_id:
        emp = db.query(Employee).filter(Employee.employee_id == selected_emp_id).first()
        salaries = db.query(SalaryRecord).filter(SalaryRecord.employee_id == selected_emp_id).order_by(SalaryRecord.effective_date.asc()).all()
        perfs = db.query(PerformanceEvidence).filter(PerformanceEvidence.employee_id == selected_emp_id).order_by(PerformanceEvidence.effective_date.asc()).all()
        proms = db.query(Promotion).filter(Promotion.employee_id == selected_emp_id).all()
        tenure = db.query(Tenure).filter(Tenure.employee_id == selected_emp_id).first()

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Employee:** {emp.first_name} {emp.last_name}")
            st.markdown(f"**Email:** {emp.email}")
            st.markdown(f"**Department:** {emp.department}")
        with col_b:
            st.markdown(f"**Role:** {role_map.get(emp.current_role_id, emp.current_role_id)}")
            st.markdown(f"**Level:** {level_map.get(emp.current_level_id, emp.current_level_id)}")
            st.markdown(f"**Location:** {loc_map.get(emp.current_location_id, emp.current_location_id)}")
        with col_c:
            st.markdown(f"**Hire Date:** {emp.hire_date}")
            st.markdown(f"**FTE:** {emp.fte:.2f} ({emp.employment_type.replace('_', ' ').title()})")
            if tenure:
                st.markdown(f"**Company Tenure:** {tenure.tenure_in_company_years:.1f} yrs (Total experience: {tenure.years_of_experience_total:.1f} yrs)")

        # Salary Trajectory Chart
        if salaries:
            sal_df = pd.DataFrame([
                {
                    "Effective Date": str(s.effective_date),
                    "Normalized Salary (USD)": float(s.normalized_salary),
                    "Base Salary": float(s.base_salary),
                    "Currency": s.currency,
                    "Change Reason": s.change_reason.replace("_", " ").title(),
                }
                for s in salaries
            ])

            fig_traj = px.line(
                sal_df,
                x="Effective Date",
                y="Normalized Salary (USD)",
                markers=True,
                title=f"Compensation Trajectory — {emp.first_name} {emp.last_name}"
            )
            fig_traj.update_traces(
                marker=dict(size=9),
                hovertemplate="Date: %{x}<br>Normalized Salary: $%{y:,.0f}<extra></extra>"
            )
            apply_clean_layout(fig_traj, legend_bottom=False, height=380)
            st.plotly_chart(fig_traj, use_container_width=True, config=PLOTLY_CONFIG)

            st.write("Historical Compensation Records:")
            st.dataframe(
                sal_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Normalized Salary (USD)": st.column_config.NumberColumn("Normalized Salary (USD)", format="$%,.0f"),
                    "Base Salary": st.column_config.NumberColumn("Base Salary (Local)", format="%,.0f"),
                },
            )

        if perfs:
            st.write("Performance Evaluation Reviews:")
            perf_df = pd.DataFrame([
                {
                    "Review Cycle": p.review_cycle,
                    "Rating Score": float(p.rating_score),
                    "Rating Label": p.rating_label,
                    "Skills Score": float(p.documented_skills_score) if p.documented_skills_score is not None else 0.0,
                    "Critical Initiatives": int(p.critical_initiative_count),
                    "Review Date": str(p.effective_date)
                }
                for p in perfs
            ])
            st.dataframe(
                perf_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rating Score": st.column_config.NumberColumn("Rating Score", format="%.2f"),
                    "Skills Score": st.column_config.NumberColumn("Skills Score", format="%.1f"),
                },
            )

        if proms:
            st.write("Promotion History:")
            prom_df = pd.DataFrame([
                {
                    "Promotion ID": p.promotion_id,
                    "From Level": level_map.get(p.from_level_id, p.from_level_id),
                    "To Level": level_map.get(p.to_level_id, p.to_level_id),
                    "Effective Date": str(p.effective_date),
                    "Reason": p.promotion_reason
                }
                for p in proms
            ])
            st.dataframe(prom_df, use_container_width=True, hide_index=True)
