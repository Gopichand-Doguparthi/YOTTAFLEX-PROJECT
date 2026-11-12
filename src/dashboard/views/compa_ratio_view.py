"""
View 4: Compa-Ratio Analysis.
Compa-ratio = Normalized employee salary divided by the applicable compensation band midpoint.
Audits distribution against the target market parity range of 0.80 to 1.20.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.compa_ratio import CompaRatioCalculator
from src.dashboard.views.helpers import get_role_map, get_level_map, get_location_map, PLOTLY_CONFIG


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compa-Ratio Distribution & Market Parity Benchmarking")
    st.markdown(
        "The **Compa-Ratio** measures how an employee's salary compares to the midpoint of their applicable "
        "compensation band. A value of 1.00 represents exact market parity; values below 0.80 indicate "
        "underpayment risk and values above 1.20 indicate potential over-market positioning."
    )

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)

    emp_query = db.query(Employee)
    if selected_role != "All":
        emp_query = emp_query.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        emp_query = emp_query.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        emp_query = emp_query.filter(Employee.current_location_id == selected_location)
    employees = emp_query.all()

    salaries = db.query(SalaryRecord).filter(SalaryRecord.effective_date >= "2026-01-01").all()
    latest_sals = {s.employee_id: s for s in salaries}

    bands = db.query(CompensationBand).filter(CompensationBand.status == "ACTIVE").all()
    band_lookup = {(b.role_id, b.level_id, b.location_id): b for b in bands}

    data = []
    for emp in employees:
        sal = latest_sals.get(emp.employee_id)
        if not sal:
            continue
        band = band_lookup.get((emp.current_role_id, emp.current_level_id, emp.current_location_id))
        if not band:
            continue

        cr = CompaRatioCalculator.calculate(sal.normalized_salary, band.mid_salary)
        classification = CompaRatioCalculator.classify(cr)

        data.append({
            "Employee ID": emp.employee_id,
            "Name": f"{emp.first_name} {emp.last_name}",
            "Department": emp.department,
            "Role": role_map.get(emp.current_role_id, emp.current_role_id),
            "Level": level_map.get(emp.current_level_id, emp.current_level_id),
            "Location": loc_map.get(emp.current_location_id, emp.current_location_id),
            "Salary (USD)": sal.normalized_salary,
            "Band Midpoint": band.mid_salary,
            "Compa-Ratio": cr,
            "Classification": classification
        })

    df = pd.DataFrame(data)
    if df.empty:
        st.warning("No records found for compa-ratio analysis under current filters.")
        return

    below_target = len(df[df["Classification"] == "BELOW_TARGET"])
    in_target = len(df[df["Classification"] == "TARGET_RANGE"])
    above_target = len(df[df["Classification"] == "ABOVE_TARGET"])
    avg_cr = df["Compa-Ratio"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Compa-Ratio", f"{avg_cr:.2f}")
    col2.metric("In Target Range (0.80 – 1.20)", f"{in_target} ({in_target/len(df)*100:.1f}%)")
    col3.metric("Below Target (< 0.80)", f"{below_target}", delta=f"-{below_target}", delta_color="inverse")
    col4.metric("Above Target (> 1.20)", f"{above_target}", delta=f"+{above_target}")

    st.markdown("---")

    col_hist, col_box = st.columns(2)
    with col_hist:
        fig_hist = px.histogram(
            df,
            x="Compa-Ratio",
            color="Classification",
            nbins=30,
            title="Workforce Compa-Ratio Distribution",
            color_discrete_map={
                "BELOW_TARGET": "#e74c3c",
                "TARGET_RANGE": "#2ecc71",
                "ABOVE_TARGET": "#f39c12"
            }
        )
        fig_hist.add_vline(x=0.80, line_dash="dash", line_color="red", annotation_text="Min Target (0.80)")
        fig_hist.add_vline(x=1.00, line_dash="solid", line_color="green", annotation_text="Market Parity (1.00)")
        fig_hist.add_vline(x=1.20, line_dash="dash", line_color="orange", annotation_text="Max Target (1.20)")
        st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    with col_box:
        fig_box = px.box(
            df,
            x="Department",
            y="Compa-Ratio",
            color="Department",
            title="Compa-Ratio Spread Across Departments"
        )
        fig_box.add_hline(y=1.0, line_dash="solid", line_color="gray")
        fig_box.update_layout(showlegend=False, xaxis_tickangle=-30)
        st.plotly_chart(fig_box, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Below-Target Employees (Equity Review Priority)")
    st.dataframe(df[df["Classification"] == "BELOW_TARGET"], use_container_width=True)
