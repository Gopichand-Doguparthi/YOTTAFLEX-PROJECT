"""
View 4: Compa-Ratio Analysis.
Compa-ratio compares an employee's USD-normalized salary against their applicable USD-normalized band midpoint.
Audits distribution against the target market parity range of 0.80 to 1.20.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.compa_ratio import CompaRatioCalculator
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    fmt_usd, PLOTLY_CONFIG, apply_clean_layout,
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


@st.cache_data(ttl=120, show_spinner=False)
def _load_compa_ratio_records() -> pd.DataFrame:
    """Computes and caches the 2026 Compa-Ratio dataset across all employees."""
    db = SessionLocal()
    try:
        role_map = get_role_map(db)
        level_map = get_level_map(db)
        loc_map = get_location_map(db)
        curr_norm = get_currency_normalizer(db)

        employees = db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.department,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
        ).all()

        latest_sals = {
            r[0]: float(r[1])
            for r in db.query(SalaryRecord.employee_id, SalaryRecord.normalized_salary)
            .filter(SalaryRecord.effective_date >= "2026-01-01")
            .all()
        }

        band_lookup = {
            (b.role_id, b.level_id, b.location_id): b
            for b in db.query(CompensationBand).filter(CompensationBand.status == "ACTIVE").all()
        }

        data = []
        for eid, fn, ln, dept, r_id, l_id, loc_id in employees:
            norm_sal = latest_sals.get(eid)
            if norm_sal is None:
                continue
            band = band_lookup.get((r_id, l_id, loc_id))
            if not band:
                continue

            _, mid_usd, _ = get_band_usd_amounts(band, curr_norm)
            cr = CompaRatioCalculator.calculate(norm_sal, mid_usd)
            raw_class = CompaRatioCalculator.classify(cr)

            data.append({
                "Employee ID": eid,
                "Name": f"{fn} {ln}",
                "Department": dept,
                "Role": role_map.get(r_id, r_id),
                "Level": level_map.get(l_id, l_id),
                "Location": loc_map.get(loc_id, loc_id),
                "Salary (USD)": norm_sal,
                "Band Midpoint (USD)": mid_usd,
                "Compa-Ratio": round(float(cr), 3),
                "Classification": _CLASS_LABELS.get(raw_class, raw_class),
                "_raw_class": raw_class,
                "_role_id": r_id,
                "_level_id": l_id,
                "_location_id": loc_id,
            })
        return pd.DataFrame(data)
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compa-Ratio Distribution & Market Parity Benchmarking")
    st.markdown(
        "The **Compa-Ratio** measures how an employee's salary compares to the midpoint of their applicable "
        "compensation band. A value of 1.00 represents exact market parity; values below 0.80 indicate "
        "underpayment risk and values above 1.20 indicate potential over-market positioning."
    )

    df = _load_compa_ratio_records()
    if not df.empty:
        if selected_role != "All":
            df = df[df["_role_id"] == selected_role]
        if selected_level != "All":
            df = df[df["_level_id"] == selected_level]
        if selected_location != "All":
            df = df[df["_location_id"] == selected_location]

    if df.empty:
        st.warning("No records found for compa-ratio analysis under current filters.")
        return

    below_target = int((df["_raw_class"] == "BELOW_TARGET").sum())
    in_target = int((df["_raw_class"] == "TARGET_RANGE").sum())
    above_target = int((df["_raw_class"] == "ABOVE_TARGET").sum())
    median_cr = df["Compa-Ratio"].median()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Median Compa-Ratio", f"{median_cr:.2f}")
    col2.metric("In Target Range (0.80 – 1.20)", f"{in_target:,} ({in_target/len(df)*100:.1f}%)")
    col3.metric("Below Target (< 0.80)", f"{below_target:,}", delta=f"-{below_target}", delta_color="inverse")
    col4.metric("Above Target (> 1.20)", f"{above_target:,}", delta=f"+{above_target}")

    st.markdown("---")

    df_chart = df[df["Compa-Ratio"] <= 2.0].copy()
    extreme_count = len(df) - len(df_chart)
    if extreme_count > 0:
        st.caption(
            f"Chart range focused on 0.00 – 2.00 for readability ({extreme_count} extreme exception record(s) > 2.00 are included in metrics and tables)."
        )

    col_hist, col_bar = st.columns(2)
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
            annotation_text="Min (0.80)", annotation_position="top left", annotation_yshift=-6
        )
        fig_hist.add_vline(
            x=1.00, line_dash="solid", line_color="#2ecc71",
            annotation_text="Parity (1.00)", annotation_position="top", annotation_yshift=8
        )
        fig_hist.add_vline(
            x=1.20, line_dash="dash", line_color="#f39c12",
            annotation_text="Max (1.20)", annotation_position="top right", annotation_yshift=-6
        )
        fig_hist.update_layout(yaxis_title="Employee Count", xaxis_title="Compa-Ratio")
        apply_clean_layout(fig_hist, legend_bottom=True, height=470)
        st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CONFIG)

    with col_bar:
        dept_cr = (
            df_chart.groupby("Department")["Compa-Ratio"]
            .agg(Average="mean", Median="median")
            .reset_index()
            .melt(id_vars="Department", value_vars=["Average", "Median"], var_name="Metric", value_name="Compa-Ratio")
        )
        fig_dept = px.bar(
            dept_cr,
            x="Department",
            y="Compa-Ratio",
            color="Metric",
            barmode="group",
            title="Average vs. Median Compa-Ratio by Department",
            color_discrete_map={"Average": "#6366f1", "Median": "#2ecc71"},
        )
        fig_dept.add_hline(y=1.0, line_dash="dash", line_color="#2ecc71", annotation_text="Market Parity (1.00)", annotation_position="top right")
        fig_dept.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:.3f}<extra></extra>")
        apply_clean_layout(fig_dept, legend_bottom=True, height=470, xaxis_tickangle=-25)
        st.plotly_chart(fig_dept, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Below-Target Employees (Equity Review Priority)")
    below_raw = df[df["_raw_class"] == "BELOW_TARGET"].copy()
    if below_raw.empty:
        st.success("No employees are below the 0.80 target Compa-Ratio threshold.")
    else:
        below_disp = pd.DataFrame({
            "Employee ID": below_raw["Employee ID"],
            "Name": below_raw["Name"],
            "Department": below_raw["Department"],
            "Role": below_raw["Role"],
            "Level": below_raw["Level"],
            "Location": below_raw["Location"],
            "Salary (USD)": below_raw["Salary (USD)"].map(fmt_usd),
            "Band Midpoint (USD)": below_raw["Band Midpoint (USD)"].map(fmt_usd),
            "Compa-Ratio": below_raw["Compa-Ratio"],
            "Classification": below_raw["Classification"],
        })
        st.dataframe(
            below_disp,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Compa-Ratio": st.column_config.NumberColumn("Compa-Ratio", format="%.2f"),
            },
        )
