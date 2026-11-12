"""
View 2: Employee and Salary Analytics.
Provides directory exploration (including tenure), compensation progression tracking, and profile drill-downs.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, PerformanceEvidence, Tenure, Promotion
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    fmt_usd, fmt_num, PLOTLY_CONFIG, apply_clean_layout, build_table_column_config,
)


@st.cache_data(ttl=120, show_spinner=False)
def _load_employee_directory() -> list:
    """Fetches lightweight employee + tenure tuples once and caches them."""
    db = SessionLocal()
    try:
        tenures = {
            t.employee_id: (float(t.tenure_in_company_years), float(t.years_of_experience_total))
            for t in db.query(Tenure.employee_id, Tenure.tenure_in_company_years, Tenure.years_of_experience_total).all()
        }
        rows = db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.email,
            Employee.department,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
            Employee.employment_type,
            Employee.fte,
            Employee.hire_date,
        ).all()

        result = []
        for r in rows:
            c_ten, tot_exp = tenures.get(r[0], (0.0, 0.0))
            result.append({
                "employee_id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "email": r[3],
                "department": r[4],
                "role_id": r[5],
                "level_id": r[6],
                "location_id": r[7],
                "employment_type": r[8],
                "fte": float(r[9]),
                "hire_date": str(r[10]),
                "company_tenure": round(c_ten, 1),
                "total_exp": round(tot_exp, 1),
            })
        return result
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Employee & Salary History Analytics")
    st.markdown("Detailed breakdown of workforce demographics, tenure, historical compensation events, and individual employee progression.")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    all_rows = _load_employee_directory()

    ec1, ec2, ec3 = st.columns([2, 1.5, 1.5])
    with ec1:
        search_query = st.text_input("Search by Employee ID, Name, or Email:", "", placeholder="e.g. EMP-000001 or James")
    with ec2:
        dept_opts = ["All Departments"] + sorted({e["department"] for e in all_rows})
        dept_filter = st.selectbox("Filter by Department:", dept_opts, index=0)
    with ec3:
        type_opts = ["All Types", "Full Time", "Part Time"]
        type_filter = st.selectbox("Filter by Employment Type:", type_opts, index=0)
    term = search_query.strip().lower()

    emp_data = []
    for e in all_rows:
        if selected_role != "All" and e["role_id"] != selected_role:
            continue
        if selected_level != "All" and e["level_id"] != selected_level:
            continue
        if selected_location != "All" and e["location_id"] != selected_location:
            continue
        if dept_filter != "All Departments" and e["department"] != dept_filter:
            continue
        emp_type_label = e["employment_type"].replace("_", " ").title()
        if type_filter != "All Types" and emp_type_label != type_filter:
            continue
        if term:
            if not (term in e["employee_id"].lower() or term in e["first_name"].lower()
                    or term in e["last_name"].lower() or term in e["email"].lower()):
                continue

        emp_data.append({
            "Employee ID": e["employee_id"],
            "Name": f"{e['first_name']} {e['last_name']}",
            "Department": e["department"],
            "Role": role_map.get(e["role_id"], e["role_id"]),
            "Level": level_map.get(e["level_id"], e["level_id"]),
            "Location": loc_map.get(e["location_id"], e["location_id"]),
            "Tenure (yrs)": e["company_tenure"],
            "Total Exp (yrs)": e["total_exp"],
            "Type": emp_type_label,
            "FTE": e["fte"],
            "Hire Date": e["hire_date"],
        })

    if not emp_data:
        st.warning("No employees found matching the specified filters.")
        return

    df_emps = pd.DataFrame(emp_data)
    st.caption(f"Showing {len(df_emps):,} employee records")
    st.dataframe(
        df_emps,
        use_container_width=True,
        height=340,
        hide_index=True,
        column_config=build_table_column_config(
            df_emps,
            overrides={
                "Tenure (yrs)": st.column_config.NumberColumn("Tenure (yrs)", format="%.1f"),
                "Total Exp (yrs)": st.column_config.NumberColumn("Total Exp (yrs)", format="%.1f"),
                "FTE": st.column_config.NumberColumn("FTE", format="%.2f"),
            },
        ),
    )

    # Detailed Employee Drill-down
    st.markdown("---")
    st.subheader("Employee Profile & Career Trajectory Drill-Down")

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

        if salaries:
            chart_df = pd.DataFrame([
                {
                    "Effective Date": str(s.effective_date),
                    "Normalized Salary (USD)": float(s.normalized_salary),
                }
                for s in salaries
            ])
            fig_traj = px.line(
                chart_df,
                x="Effective Date",
                y="Normalized Salary (USD)",
                markers=True,
                title=f"Compensation Trajectory — {emp.first_name} {emp.last_name}"
            )
            fig_traj.update_traces(
                marker=dict(size=9),
                hovertemplate="Date: %{x}<br>Normalized Salary: $%{y:,.0f}<extra></extra>"
            )
            apply_clean_layout(fig_traj, legend_bottom=False, height=400)
            st.plotly_chart(fig_traj, use_container_width=True, config=PLOTLY_CONFIG)

            sal_table_df = pd.DataFrame([
                {
                    "Effective Date": str(s.effective_date),
                    "Normalized Salary (USD)": fmt_usd(s.normalized_salary),
                    "Base Salary (Local)": fmt_num(s.base_salary, 0),
                    "Currency": s.currency,
                    "Change Reason": s.change_reason.replace("_", " ").title(),
                }
                for s in salaries
            ])
            st.write("Historical Compensation Records:")
            st.dataframe(
                sal_table_df,
                use_container_width=True,
                hide_index=True,
                column_config=build_table_column_config(sal_table_df),
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
                column_config=build_table_column_config(
                    perf_df,
                    overrides={
                        "Rating Score": st.column_config.NumberColumn("Rating Score", format="%.2f"),
                        "Skills Score": st.column_config.NumberColumn("Skills Score", format="%.1f"),
                    },
                ),
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
            st.dataframe(
                prom_df,
                use_container_width=True,
                hide_index=True,
                column_config=build_table_column_config(prom_df),
            )

    st.markdown("---")
    with st.expander("Create / Manage Employee", expanded=False):
        from datetime import date as _date
        from src.workflow.audit_logger import AuditLogger

        with st.form("create_employee_form"):
            ce1, ce2, ce3 = st.columns(3)
            with ce1:
                new_emp_id = st.text_input("Employee ID:", placeholder="EMP-900001")
                new_fname = st.text_input("First Name:")
                new_lname = st.text_input("Last Name:")
                new_email = st.text_input("Email:")
            with ce2:
                new_dept = st.text_input("Department:", "Engineering")
                new_role = st.selectbox("Role ID:", sorted(role_map.keys()), key="ce_role")
                new_lvl = st.selectbox("Level ID:", sorted(level_map.keys()), key="ce_lvl")
            with ce3:
                new_loc = st.selectbox("Location ID:", sorted(loc_map.keys()), key="ce_loc")
                new_type = st.selectbox("Employment Type:", ["FULL_TIME", "PART_TIME", "CONTRACT"], key="ce_type")
                new_fte = st.number_input("FTE:", min_value=0.1, max_value=1.0, value=1.0, step=0.1)
                new_hire = st.date_input("Hire Date:", value=_date(2026, 1, 1))

            if st.form_submit_button("Create Employee"):
                if not new_emp_id.strip() or not new_fname.strip() or not new_lname.strip() or "@" not in new_email:
                    st.error("All required fields (Employee ID, First/Last Name, valid Email) must be provided.")
                elif db.query(Employee).filter(Employee.employee_id == new_emp_id.strip()).first():
                    st.error(f"Duplicate Employee ID '{new_emp_id.strip()}' already exists.")
                elif db.query(Employee).filter(Employee.email == new_email.strip()).first():
                    st.error(f"Duplicate Email '{new_email.strip()}' already exists.")
                else:
                    emp_obj = Employee(
                        employee_id=new_emp_id.strip(),
                        first_name=new_fname.strip(),
                        last_name=new_lname.strip(),
                        email=new_email.strip(),
                        department=new_dept.strip() or "Engineering",
                        current_role_id=new_role,
                        current_level_id=new_lvl,
                        current_location_id=new_loc,
                        hire_date=new_hire,
                        employment_type=new_type,
                        fte=float(new_fte),
                        is_active=True,
                    )
                    db.add(emp_obj)
                    AuditLogger.log_event(
                        session=db,
                        entity_name="Employee",
                        entity_id=emp_obj.employee_id,
                        event_type="EMPLOYEE_CREATED",
                        actor_id="HR_DASHBOARD",
                        actor_role="HR_PARTNER",
                        new_state={"role_id": new_role, "level_id": new_lvl, "fte": float(new_fte)},
                    )
                    db.commit()
                    st.cache_data.clear()
                    st.success(f"Created employee {emp_obj.employee_id} and logged audit event.")
