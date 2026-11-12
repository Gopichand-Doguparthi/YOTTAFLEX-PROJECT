"""
View 5: Within-Band Position Analysis.
Within-band position measures how far along the USD-normalized salary band range an employee sits —
from 0% (at the minimum) to 100% (at the maximum).
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.within_band import WithinBandCalculator
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    PLOTLY_CONFIG, apply_clean_layout,
)


_ZONE_LABELS = {
    "GREEN_CIRCLED": "Green-Circled (< 0%)",
    "LOWER_QUARTILE": "Lower Quartile (0%–25%)",
    "MID_LOWER": "Mid-Lower (25%–50%)",
    "MID_UPPER": "Mid-Upper (50%–75%)",
    "UPPER_QUARTILE": "Upper Quartile (75%–100%)",
    "RED_CIRCLED": "Red-Circled (> 100%)",
}

_ZONE_COLORS = {
    "Green-Circled (< 0%)": "#2ecc71",
    "Lower Quartile (0%–25%)": "#3498db",
    "Mid-Lower (25%–50%)": "#1abc9c",
    "Mid-Upper (50%–75%)": "#6366f1",
    "Upper Quartile (75%–100%)": "#f39c12",
    "Red-Circled (> 100%)": "#e74c3c",
}


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Within-Band Position & Range Placement Analysis")
    st.markdown(
        "**Within-Band Position** shows where an employee's salary sits within their compensation band, "
        "expressed as a percentage from 0% (band minimum) to 100% (band maximum). "
        "Employees below 0% are **Green-Circled** (underpaid below the band minimum); "
        "those above 100% are **Red-Circled** (paid above the band ceiling)."
    )

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)
    curr_norm = get_currency_normalizer(db)

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

        min_usd, _, max_usd = get_band_usd_amounts(band, curr_norm)
        wbp = WithinBandCalculator.calculate(sal.normalized_salary, min_usd, max_usd)
        raw_zone = WithinBandCalculator.classify_zone(wbp)

        data.append({
            "Employee ID": emp.employee_id,
            "Name": f"{emp.first_name} {emp.last_name}",
            "Zone": _ZONE_LABELS.get(raw_zone, raw_zone),
            "Position (%)": round(wbp * 100, 1),
            "Salary (USD)": float(sal.normalized_salary),
            "Band Min (USD)": min_usd,
            "Band Max (USD)": max_usd,
            "Department": emp.department,
            "Role": role_map.get(emp.current_role_id, emp.current_role_id),
            "Level": level_map.get(emp.current_level_id, emp.current_level_id),
            "Location": loc_map.get(emp.current_location_id, emp.current_location_id),
            "_raw_zone": raw_zone,
        })

    df = pd.DataFrame(data)
    if df.empty:
        st.warning("No records found for within-band position analysis.")
        return

    green_circled = len(df[df["_raw_zone"] == "GREEN_CIRCLED"])
    red_circled = len(df[df["_raw_zone"] == "RED_CIRCLED"])
    in_band = len(df) - (green_circled + red_circled)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Median Band Placement", f"{df['Position (%)'].median():.1f}%")
    col2.metric("Within Band (0% – 100%)", f"{in_band:,} ({in_band/len(df)*100:.1f}%)")
    with col3:
        st.metric("Green-Circled (< 0%)", f"{green_circled:,}")
        st.markdown('<span style="color:#2ecc71; font-size:0.82rem; font-weight:600;">● Underpaid below minimum</span>', unsafe_allow_html=True)
    with col4:
        st.metric("Red-Circled (> 100%)", f"{red_circled:,}")
        st.markdown('<span style="color:#e74c3c; font-size:0.82rem; font-weight:600;">● Above band ceiling</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Focus scatter on normal analytical range [-100%, 200%] so extreme FX/FTE anomaly points don't collapse the chart
    df_chart = df[(df["Position (%)"] >= -100.0) & (df["Position (%)"] <= 200.0)].copy()
    extreme_count = len(df) - len(df_chart)
    if extreme_count > 0:
        st.caption(
            f"Scatter plot focused on -100% to 200% for clarity ({extreme_count} extreme exception record(s) outside this range appear in metrics and the outliers table)."
        )

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
            color_discrete_map=_ZONE_COLORS,
            category_orders={"Zone": list(_ZONE_COLORS.keys())},
        )
        apply_clean_layout(fig_pie, legend_bottom=True, height=460)
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_chart2:
        fig_scatter = px.scatter(
            df_chart,
            x="Position (%)",
            y="Salary (USD)",
            color="Zone",
            color_discrete_map=_ZONE_COLORS,
            category_orders={"Zone": list(_ZONE_COLORS.keys())},
            hover_data=["Employee ID", "Name", "Role", "Level", "Location"],
            title="Salary vs Within-Band Percentage"
        )
        fig_scatter.add_vline(
            x=0.0, line_dash="dash", line_color="#2ecc71",
            annotation_text="Band Min (0%)", annotation_position="top left"
        )
        fig_scatter.add_vline(
            x=100.0, line_dash="dash", line_color="#e74c3c",
            annotation_text="Band Max (100%)", annotation_position="top right"
        )
        apply_clean_layout(fig_scatter, legend_bottom=True, height=460)
        st.plotly_chart(fig_scatter, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Range Outliers: Green-Circled & Red-Circled Employees")
    outliers = df[df["_raw_zone"].isin(["GREEN_CIRCLED", "RED_CIRCLED"])].drop(columns=["_raw_zone"])
    if outliers.empty:
        st.success("No Green-Circled or Red-Circled range outliers found under the current filters.")
    else:
        st.caption(f"{len(outliers):,} range outlier record(s) found")
        st.dataframe(
            outliers,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Employee ID": st.column_config.TextColumn("Employee ID", width="small"),
                "Name": st.column_config.TextColumn("Employee Name", width="medium"),
                "Zone": st.column_config.TextColumn("Band Zone", width="medium"),
                "Position (%)": st.column_config.NumberColumn("Position (%)", format="%.1f%%", width="small"),
                "Salary (USD)": st.column_config.NumberColumn("Salary (USD)", format="$%,.0f", width="small"),
                "Band Min (USD)": st.column_config.NumberColumn("Band Min (USD)", format="$%,.0f", width="small"),
                "Band Max (USD)": st.column_config.NumberColumn("Band Max (USD)", format="$%,.0f", width="small"),
                "Role": st.column_config.TextColumn("Role", width="medium"),
                "Level": st.column_config.TextColumn("Level", width="medium"),
                "Location": st.column_config.TextColumn("Location", width="medium"),
            },
        )
