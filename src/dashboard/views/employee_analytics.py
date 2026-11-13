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
            Employee.is_active,
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
                "is_active": bool(r[11]),
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
        type_opts = ["All Types", "Full Time", "Part Time", "Contract"]
        type_filter = st.selectbox("Filter by Employment Type:", type_opts, index=0)

    ec4, ec5, ec6, ec7 = st.columns(4)
    with ec4:
        status_filter = st.selectbox("Active Status:", ["All", "Active Only", "Inactive Only"], index=0, key="emp_status_filter")
    with ec5:
        hire_years = sorted({e["hire_date"][:4] for e in all_rows if e.get("hire_date")}, reverse=True)
        hire_year_filter = st.selectbox("Hire Year:", ["All Years"] + hire_years, index=0, key="emp_hire_yr_filter")
    with ec6:
        fte_filter = st.selectbox("FTE Range:", ["All FTE", "Full-Time (1.0)", "Part-Time (< 1.0)"], index=0, key="emp_fte_filter")
    with ec7:
        sort_by = st.selectbox("Sort By:", ["Employee ID (Asc)", "Name (A-Z)", "Tenure (High-Low)", "Hire Date (Newest)"], index=0, key="emp_sort_by")
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
        if status_filter == "Active Only" and not e.get("is_active", True):
            continue
        if status_filter == "Inactive Only" and e.get("is_active", True):
            continue
        if hire_year_filter != "All Years" and not str(e.get("hire_date", "")).startswith(hire_year_filter):
            continue
        if fte_filter == "Full-Time (1.0)" and e["fte"] < 1.0:
            continue
        if fte_filter == "Part-Time (< 1.0)" and e["fte"] >= 1.0:
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
            "Active": "Active" if e.get("is_active", True) else "Inactive",
        })

    if not emp_data:
        st.warning("No employees found matching the specified filters.")
        df_emps = pd.DataFrame()
    else:
        df_emps = pd.DataFrame(emp_data)
        if sort_by == "Name (A-Z)":
            df_emps = df_emps.sort_values("Name")
        elif sort_by == "Tenure (High-Low)":
            df_emps = df_emps.sort_values("Tenure (yrs)", ascending=False)
        elif sort_by == "Hire Date (Newest)":
            df_emps = df_emps.sort_values("Hire Date", ascending=False)
        else:
            df_emps = df_emps.sort_values("Employee ID")

    if not df_emps.empty:
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
    else:
        selected_emp_id = None

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
    fb = st.session_state.pop("emp_manage_feedback", None)
    if fb:
        fb_level, fb_msg = fb
        if fb_level == "success":
            st.success(fb_msg)
        elif fb_level == "warning":
            st.warning(fb_msg)
        else:
            st.error(fb_msg)

    # Keep expander open if user is actively creating or managing/deleting employees
    manage_in_use = (
        st.session_state.get("emp_manage_open", False)
        or bool(st.session_state.get("del_search_name"))
        or bool(st.session_state.get("del_emp_pick"))
        or bool(st.session_state.get("del_emp_id"))
        or bool(st.session_state.get("del_emp_confirm"))
        or (st.session_state.get("del_dept_filter") not in (None, "All Departments"))
        or (st.session_state.get("del_status_filter") not in (None, "All"))
    )
    with st.expander("Create / Manage / Delete Employee", expanded=manage_in_use):
        from datetime import date as _date
        from src.workflow.audit_logger import AuditLogger
        from src.engine.currency_normalizer import CurrencyNormalizer, MissingCurrencyConversionException
        from src.engine.fte_normalizer import FTENormalizer

        tab_create, tab_manage = st.tabs(["Create New Employee", "Deactivate / Delete Employee"])

        with tab_create:
            dept_choices = sorted({"Engineering", "Data & AI", "Product", "Design", "Operations", "Finance", "Human Resources", "Sales", "Legal"} | {e["department"] for e in all_rows if e.get("department")})
            with st.form("create_employee_form"):
                ce1, ce2, ce3 = st.columns(3)
                with ce1:
                    new_emp_id = st.text_input("Employee ID *:", placeholder="e.g. EMP-900001")
                    new_fname = st.text_input("First Name *:", placeholder="e.g. Jane")
                    new_lname = st.text_input("Last Name *:", placeholder="e.g. Doe")
                    new_email = st.text_input("Email *:", placeholder="e.g. jane.doe@company.org")
                    new_dept = st.selectbox("Department *:", dept_choices, index=0, key="ce_dept")
                with ce2:
                    new_role = st.selectbox("Role ID *:", sorted(role_map.keys()), key="ce_role")
                    new_lvl = st.selectbox("Level ID *:", sorted(level_map.keys()), key="ce_lvl")
                    new_loc = st.selectbox("Location ID *:", sorted(loc_map.keys()), key="ce_loc")
                    new_type = st.selectbox("Employment Type *:", ["FULL_TIME", "PART_TIME", "CONTRACT"], key="ce_type")
                    new_fte = st.number_input("FTE *:", min_value=0.1, max_value=1.0, value=1.0, step=0.1)
                with ce3:
                    new_hire = st.date_input("Hire Date *:", value=_date(2026, 1, 1))
                    new_base_sal = st.number_input("Initial Base Salary (Local) *:", min_value=1000.0, value=120000.0, step=1000.0)
                    new_curr = st.selectbox("Salary Currency *:", ["USD", "GBP", "EUR", "INR", "JPY", "SGD", "AUD", "CAD"], index=0, key="ce_curr")
                    new_freq = st.selectbox("Pay Frequency *:", ["ANNUAL", "MONTHLY"], index=0, key="ce_freq")
                    new_exp = st.number_input("Total Experience (yrs) *:", min_value=0.0, max_value=50.0, value=3.0, step=0.5)
                    new_rating = st.number_input("Initial Performance Rating (1.0-5.0) *:", min_value=1.0, max_value=5.0, value=3.5, step=0.1)

                if fb:
                    fb_level, fb_msg = fb
                    if fb_level == "success":
                        st.success(fb_msg)
                    elif fb_level == "warning":
                        st.warning(fb_msg)
                    else:
                        st.error(fb_msg)

                if st.form_submit_button("Create Employee with Initial Compensation"):
                    st.session_state["emp_manage_open"] = True
                    if (
                        not new_emp_id.strip()
                        or not new_fname.strip()
                        or not new_lname.strip()
                        or "@" not in new_email
                        or not new_dept.strip()
                    ):
                        st.session_state["emp_manage_feedback"] = ("error", "All required fields (*: Employee ID, First/Last Name, valid Email, Department) must be provided.")
                        st.rerun()
                    elif db.query(Employee).filter(Employee.employee_id == new_emp_id.strip()).first():
                        st.session_state["emp_manage_feedback"] = ("error", f"Duplicate Employee ID '{new_emp_id.strip()}' already exists.")
                        st.rerun()
                    elif db.query(Employee).filter(Employee.email == new_email.strip()).first():
                        st.session_state["emp_manage_feedback"] = ("error", f"Duplicate Email '{new_email.strip()}' already exists.")
                        st.rerun()
                    else:
                        curr_norm = CurrencyNormalizer()
                        curr_norm.load_from_db(db)
                        try:
                            fx_rate = curr_norm.get_rate(new_curr, "USD", new_hire)
                        except MissingCurrencyConversionException as exc:
                            st.session_state["emp_manage_feedback"] = ("error", f"Cannot create salary record: {exc}")
                            fx_rate = None
                            st.rerun()

                        if fx_rate is not None:
                            norm_sal = FTENormalizer.normalize_salary(
                                base_salary=float(new_base_sal),
                                fte=float(new_fte),
                                pay_frequency=new_freq,
                                fx_rate=fx_rate,
                            )
                            eid = new_emp_id.strip()
                            emp_obj = Employee(
                                employee_id=eid,
                                first_name=new_fname.strip(),
                                last_name=new_lname.strip(),
                                email=new_email.strip(),
                                department=new_dept.strip(),
                                current_role_id=new_role,
                                current_level_id=new_lvl,
                                current_location_id=new_loc,
                                hire_date=new_hire,
                                employment_type=new_type,
                                fte=float(new_fte),
                                is_active=True,
                            )
                            sal_obj = SalaryRecord(
                                salary_id=f"SAL-{eid}-{new_hire.year}-01",
                                employee_id=eid,
                                base_salary=float(new_base_sal),
                                currency=new_curr,
                                fte=float(new_fte),
                                pay_frequency=new_freq,
                                normalized_salary=norm_sal,
                                normalized_currency="USD",
                                effective_date=new_hire,
                                change_reason="HIRE",
                            )
                            ten_obj = Tenure(
                                tenure_id=f"TEN-{eid}",
                                employee_id=eid,
                                company_start_date=new_hire,
                                role_start_date=new_hire,
                                years_of_experience_total=float(new_exp),
                                tenure_in_company_years=0.5,
                                tenure_in_role_years=0.5,
                            )
                            rating_lbl = "OUTSTANDING" if new_rating >= 4.5 else ("EXCEEDS_EXPECTATIONS" if new_rating >= 3.5 else "MEETS_EXPECTATIONS")
                            perf_obj = PerformanceEvidence(
                                evidence_id=f"PERF-{eid}-{new_hire.year}-H1",
                                employee_id=eid,
                                review_cycle=f"{new_hire.year}-H1",
                                rating_score=float(new_rating),
                                rating_label=rating_lbl,
                                effective_date=new_hire,
                            )
                            db.add_all([emp_obj, sal_obj, ten_obj, perf_obj])
                            AuditLogger.log_event(
                                session=db,
                                entity_name="Employee",
                                entity_id=eid,
                                event_type="EMPLOYEE_CREATED",
                                actor_id="HR_DASHBOARD",
                                actor_role="HR_PARTNER",
                                new_state={
                                    "role_id": new_role,
                                    "level_id": new_lvl,
                                    "fte": float(new_fte),
                                    "normalized_salary_usd": norm_sal,
                                },
                            )
                            db.commit()
                            st.cache_data.clear()
                            st.session_state["emp_manage_feedback"] = ("success", f"Created employee {eid} with initial salary (${norm_sal:,.2f} USD), tenure, and performance record.")
                            st.rerun()

        with tab_manage:
            st.markdown("##### Filter & Search Employee to Deactivate or Delete")
            st.caption("Filter by department and active status, or search by name / employee ID to select an employee.")

            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 2])
            with f_col1:
                manage_dept_choices = ["All Departments"] + sorted({e["department"] for e in all_rows if e.get("department")})
                manage_dept = st.selectbox("Filter by Department:", manage_dept_choices, index=0, key="del_dept_filter")
            with f_col2:
                manage_status = st.selectbox("Filter by Status:", ["All", "Active Only", "Inactive Only"], index=0, key="del_status_filter")
            with f_col3:
                name_search = st.text_input("Search by Name or Employee ID:", placeholder="e.g. John or EMP-000120", key="del_search_name")

            # Filter candidates from cached directory
            candidates = all_rows
            if manage_dept != "All Departments":
                candidates = [e for e in candidates if e.get("department") == manage_dept]
            if manage_status == "Active Only":
                candidates = [e for e in candidates if e.get("is_active")]
            elif manage_status == "Inactive Only":
                candidates = [e for e in candidates if not e.get("is_active")]

            search_val = (name_search or "").strip().lower()
            if search_val:
                candidates = [
                    e for e in candidates
                    if search_val in e.get("employee_id", "").lower()
                    or search_val in f"{e.get('first_name', '')} {e.get('last_name', '')}".lower()
                    or search_val in e.get("email", "").lower()
                ]

            candidate_options = ["-- Select an employee from search results --"] + [
                f"{e['employee_id']} | {e['first_name']} {e['last_name']} ({e['department']} - {e.get('role_id', '')})"
                for e in candidates[:300]
            ]

            selected_candidate_str = st.selectbox(
                f"Matching Employees ({len(candidates)} found):",
                candidate_options,
                index=0,
                key="del_emp_pick",
            )

            picked_id = ""
            if selected_candidate_str != "-- Select an employee from search results --":
                picked_id = selected_candidate_str.split(" | ")[0].strip()

            manual_id = st.text_input(
                "Selected / Manual Employee ID:",
                value=picked_id,
                placeholder="e.g. EMP-000001",
                key="del_emp_id",
            )

            target_id = manual_id.strip() if manual_id else picked_id

            target_emp = None
            if target_id:
                target_emp = db.query(Employee).filter(Employee.employee_id == target_id).first()
                if target_emp:
                    status_badge = "🟢 Active" if target_emp.is_active else "🔴 Inactive"
                    role_title = role_map.get(target_emp.current_role_id, target_emp.current_role_id)
                    lvl_title = level_map.get(target_emp.current_level_id, target_emp.current_level_id)
                    loc_title = loc_map.get(target_emp.current_location_id, target_emp.current_location_id)

                    st.info(
                        f"**Employee to Manage:**\n\n"
                        f"- **ID**: `{target_emp.employee_id}` | **Name**: **{target_emp.first_name} {target_emp.last_name}** | **Email**: `{target_emp.email}`\n"
                        f"- **Department**: {target_emp.department} | **Status**: {status_badge}\n"
                        f"- **Role**: {role_title} (`{target_emp.current_role_id}`) | **Level**: {lvl_title} (`{target_emp.current_level_id}`) | **Location**: {loc_title}\n"
                        f"- **FTE**: {target_emp.fte} | **Employment**: {target_emp.employment_type} | **Hire Date**: {target_emp.hire_date}"
                    )
                else:
                    st.warning(f"Employee ID `{target_id}` was not found in the database.")

            st.write("---")
            confirm_del = st.checkbox(
                "Confirm permanent deletion (cannot be undone)",
                value=st.session_state.get("del_emp_confirm", False),
                key="del_emp_confirm",
            )

            mc1, mc2 = st.columns(2)
            if mc1.button("Deactivate Employee", key="btn_deact_emp", use_container_width=True):
                st.session_state["emp_manage_open"] = True
                if not target_id:
                    st.session_state["emp_manage_feedback"] = ("error", "Please search, select, or enter an Employee ID first.")
                elif not target_emp:
                    st.session_state["emp_manage_feedback"] = ("error", f"Employee '{target_id}' not found.")
                else:
                    target_emp.is_active = False
                    AuditLogger.log_event(
                        session=db,
                        entity_name="Employee",
                        entity_id=target_emp.employee_id,
                        event_type="EMPLOYEE_UPDATED",
                        actor_id="HR_DASHBOARD",
                        actor_role="HR_PARTNER",
                        old_state={"is_active": True},
                        new_state={"is_active": False},
                    )
                    db.commit()
                    st.cache_data.clear()
                    st.session_state["emp_manage_feedback"] = ("warning", f"Employee {target_emp.employee_id} ({target_emp.first_name} {target_emp.last_name}) has been deactivated.")
                st.rerun()

            if mc2.button("Delete Employee Permanently", key="btn_del_emp", use_container_width=True):
                st.session_state["emp_manage_open"] = True
                if not target_id:
                    st.session_state["emp_manage_feedback"] = ("error", "Please search, select, or enter an Employee ID first.")
                elif not confirm_del:
                    st.session_state["emp_manage_feedback"] = ("error", "Please check the permanent deletion confirmation box first.")
                elif not target_emp:
                    st.session_state["emp_manage_feedback"] = ("error", f"Employee '{target_id}' not found.")
                else:
                    eid_del = target_emp.employee_id
                    emp_name = f"{target_emp.first_name} {target_emp.last_name}"
                    old_del_state = {
                        "name": emp_name,
                        "department": target_emp.department,
                        "role_id": target_emp.current_role_id,
                    }
                    from src.database.models import ReviewCase
                    db.query(ReviewCase).filter(ReviewCase.employee_id == eid_del).delete()
                    db.query(PerformanceEvidence).filter(PerformanceEvidence.reviewer_id == eid_del).update({"reviewer_id": None})
                    db.delete(target_emp)
                    AuditLogger.log_event(
                        session=db,
                        entity_name="Employee",
                        entity_id=eid_del,
                        event_type="EMPLOYEE_DELETED",
                        actor_id="HR_DASHBOARD",
                        actor_role="HR_PARTNER",
                        old_state=old_del_state,
                        new_state={"deleted": True},
                        notes=f"Employee {eid_del} ({emp_name}) permanently deleted via dashboard.",
                    )
                    db.commit()
                    st.cache_data.clear()
                    st.session_state.pop("del_emp_pick", None)
                    st.session_state.pop("del_emp_id", None)
                    st.session_state["del_emp_confirm"] = False
                    st.session_state["emp_manage_feedback"] = ("success", f"Employee {eid_del} ({emp_name}) was permanently deleted and logged in the audit trail.")
                st.rerun()
