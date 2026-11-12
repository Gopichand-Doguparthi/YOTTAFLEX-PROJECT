"""
View 4: Compa-Ratio Analysis.
Compa-ratio compares an employee's USD-normalized salary against their applicable USD-normalized band midpoint.
Audits distribution against the target market parity range of 0.80 to 1.20.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.compa_ratio import CompaRatioCalculator
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    PLOTLY_CONFIG, apply_clean_layout,
)


_CLASS_LABELS = {
    "BELOW_TARGET": "Below Target (< 0.80)",
    "TARGET_RANGE": "Target Range (0.80 – 1.20)",
    "ABOVE_TARGET": "Above Target (> 1.20)",
}

_CLASS_COLORS = {
    "Below Target (< 0.80)": "#e74c3c",
    "Target Range (0.80 – 1.20)": "#2ecc71",
    "Above Target (> 1.20)": "#f39c12",
}


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

        _, mid_usd, _ = get_band_usd_amounts(band, curr_norm)
        cr = CompaRatioCalculator.calculate(sal.normalized_salary, mid_usd)
        raw_class = CompaRatioCalculator.classify(cr)

        data.append({
            "Employee ID": emp.employee_id,
            "Name": f"{emp.first_name} {emp.last_name}",
            "Department": emp.department,
            "Role": role_map.get(emp.current_role_id, emp.current_role_id),
            "Level": level_map.get(emp.current_level_id, emp.current_level_id),
            "Location": loc_map.get(emp.current_location_id, emp.current_location_id),
            "Salary (USD)": float(sal.normalized_salary),
            "Band Midpoint (USD)": mid_usd,
            "Compa-Ratio": round(float(cr), 3),
            "Classification": _CLASS_LABELS.get(raw_class, raw_class),
            "_raw_class": raw_class,
        })

    df = pd.DataFrame(data)
    if df.empty:
        st.warning("No records found for compa-ratio analysis under current filters.")
        return

    below_target = len(df[df["_raw_class"] == "BELOW_TARGET"])
    in_target = len(df[df["_raw_class"] == "TARGET_RANGE"])
    above_target = len(df[df["_raw_class"] == "ABOVE_TARGET"])
    median_cr = df["Compa-Ratio"].median()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Median Compa-Ratio", f"{median_cr:.2f}")
    col2.metric("In Target Range (0.80 – 1.20)", f"{in_target:,} ({in_target/len(df)*100:.1f}%)")
    col3.metric("Below Target (< 0.80)", f"{below_target:,}", delta=f"-{below_target}", delta_color="inverse")
    col4.metric("Above Target (> 1.20)", f"{above_target:,}", delta=f"+{above_target}")

    st.markdown("---")

    # Separate extreme anomaly values (> 2.0) from chart view so distribution bars aren't squished
    df_chart = df[df["Compa-Ratio"] <= 2.0].copy()
    extreme_count = len(df) - len(df_chart)
    if extreme_count > 0:
        st.caption(
            f"Chart range focused on 0.00 – 2.00 for readability ({extreme_count} extreme exception record(s) > 2.00 are included in metrics and tables)."
        )

    col_hist, col_box = st.columns(2)
    with col_hist:
        fig_hist = px.histogram(
            df_chart,
            x="Compa-Ratio",
            color="Classification",
            nbins=35,
            barmode="stack",
            title="Workforce Compa-Ratio Distribution",
            color_discrete_map=_CLASS_COLORS,
            category_orders={"Classification": list(_CLASS_COLORS.keys())},
        )
        fig_hist.add_vline(
            x=0.80, line_dash="dash", line_color="#e74c3c",
            annotation_text="Min (0.80)", annotation_position="top left",
            annotation_yshift=-4
        )
        fig_hist.add_vline(
            x=1.00, line_dash="solid", line_color="#2ecc71",
            annotation_text="Parity (1.00)", annotation_position="top",
            annotation_yshift=10
        )
        fig_hist.add_vline(
            x=1.20, line_dash="dash", line_color="#f39c12",
            annotation_text="Max (1.20)", annotation_position="top right",
            annotation_yshift=-4
        )
        fig_hist.update_layout(yaxis_title="Employee Count", xaxis_title="Compa-Ratio")
        apply_clean_layout(fig_hist, legend_bottom=True, height=460)
        st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    with col_box:
        fig_box = px.box(
            df_chart,
            x="Department",
            y="Compa-Ratio",
            color="Department",
            title="Compa-Ratio Spread Across Departments",
        )
        fig_box.add_hline(y=0.80, line_dash="dash", line_color="#e74c3c")
        fig_box.add_hline(y=1.00, line_dash="solid", line_color="#2ecc71")
        fig_box.add_hline(y=1.20, line_dash="dash", line_color="#f39c12")
        apply_clean_layout(fig_box, legend_bottom=False, height=460, xaxis_tickangle=-25)
        fig_box.update_layout(showlegend=False, yaxis_title="Compa-Ratio")
        st.plotly_chart(fig_box, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Below-Target Employees (Equity Review Priority)")
    below_df = df[df["_raw_class"] == "BELOW_TARGET"].drop(columns=["_raw_class"])
    if below_df.empty:
        st.success("No employees are below the 0.80 target Compa-Ratio threshold.")
    else:
        st.dataframe(
            below_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Salary (USD)": st.column_config.NumberColumn("Salary (USD)", format="$%,.0f"),
                "Band Midpoint (USD)": st.column_config.NumberColumn("Band Midpoint (USD)", format="$%,.0f"),
                "Compa-Ratio": st.column_config.NumberColumn("Compa-Ratio", format="%.2f"),
            },
        )
