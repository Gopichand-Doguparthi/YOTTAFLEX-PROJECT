"""
View 5: Within-Band Position Analysis.
Within-band position = (Normalized salary - Band minimum) / (Band maximum - Band minimum).
Evaluates employee placement across salary band range.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.within_band import WithinBandCalculator


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Within-Band Position & Range Placement Analysis")
    st.markdown(r"$$\text{Within-Band Position} = \frac{\text{Normalized Salary} - \text{Band Minimum}}{\text{Band Maximum} - \text{Band Minimum}}$$")

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

        wbp = WithinBandCalculator.calculate(sal.normalized_salary, band.min_salary, band.max_salary)
        zone = WithinBandCalculator.classify_zone(wbp)

        data.append({
            "Employee ID": emp.employee_id,
            "Name": f"{emp.first_name} {emp.last_name}",
            "Department": emp.department,
            "Role": emp.current_role_id,
            "Level": emp.current_level_id,
            "Location": emp.current_location_id,
            "Salary (USD)": sal.normalized_salary,
            "Band Minimum": band.min_salary,
            "Band Maximum": band.max_salary,
            "Position": wbp,
            "Position (%)": round(wbp * 100, 1),
            "Zone": zone
        })

    df = pd.DataFrame(data)
    if df.empty:
        st.warning("No records found for within-band position analysis.")
        return

    green_circled = len(df[df["Zone"] == "GREEN_CIRCLED"])
    red_circled = len(df[df["Zone"] == "RED_CIRCLED"])
    in_band = len(df) - (green_circled + red_circled)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Band Placement", f"{df['Position (%)'].mean():.1f}%")
    col2.metric("Within Band (0% - 100%)", f"{in_band} ({in_band/len(df)*100:.1f}%)")
    col3.metric("Green-Circled (< 0%)", f"{green_circled}", "Underpaid Below Minimum", delta_color="inverse")
    col4.metric("Red-Circled (> 100%)", f"{red_circled}", "Above Band Ceiling")

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        zone_counts = df["Zone"].value_counts().reset_index()
        zone_counts.columns = ["Zone", "Count"]
        fig_pie = px.pie(
            zone_counts,
            names="Zone",
            values="Count",
            title="Workforce Placement Across Band Zones",
            color="Zone",
            color_discrete_map={
                "GREEN_CIRCLED": "#e74c3c",
                "LOWER_QUARTILE": "#3498db",
                "MID_LOWER": "#1abc9c",
                "MID_UPPER": "#2ecc71",
                "UPPER_QUARTILE": "#f39c12",
                "RED_CIRCLED": "#9b59b6"
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        fig_scatter = px.scatter(
            df,
            x="Position (%)",
            y="Salary (USD)",
            color="Zone",
            hover_data=["Employee ID", "Name", "Role", "Level"],
            title="Salary vs Within-Band Percentage"
        )
        fig_scatter.add_vline(x=0.0, line_dash="dash", line_color="red")
        fig_scatter.add_vline(x=100.0, line_dash="dash", line_color="purple")
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Range Outliers: Green-Circled & Red-Circled Employees")
    outliers = df[df["Zone"].isin(["GREEN_CIRCLED", "RED_CIRCLED"])]
    st.dataframe(outliers, use_container_width=True)
