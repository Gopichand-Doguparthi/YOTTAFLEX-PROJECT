"""
View 5: Within-Band Position Analysis.
Within-band position measures how far along the USD-normalized salary band range an employee sits —
from 0% (at the minimum) to 100% (at the maximum).
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.engine.within_band import WithinBandCalculator
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    fmt_usd, fmt_pct, PLOTLY_CONFIG, apply_clean_layout,
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


@st.cache_data(ttl=120, show_spinner=False)
def _load_within_band_records() -> pd.DataFrame:
    """Computes and caches the 2026 Within-Band Position dataset across all employees."""
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

            min_usd, _, max_usd = get_band_usd_amounts(band, curr_norm)
            wbp = WithinBandCalculator.calculate(norm_sal, min_usd, max_usd)
            raw_zone = WithinBandCalculator.classify_zone(wbp)

            data.append({
                "Employee ID": eid,
                "Name": f"{fn} {ln}",
                "Band Zone": _ZONE_LABELS.get(raw_zone, raw_zone),
                "Position (%)": round(wbp * 100, 1),
                "Salary (USD)": norm_sal,
                "Band Min (USD)": min_usd,
                "Band Max (USD)": max_usd,
                "Department": dept,
                "Role": role_map.get(r_id, r_id),
                "Level": level_map.get(l_id, l_id),
                "Location": loc_map.get(loc_id, loc_id),
                "_raw_zone": raw_zone,
                "_role_id": r_id,
                "_level_id": l_id,
                "_location_id": loc_id,
            })
        return pd.DataFrame(data)
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Within-Band Position & Range Placement Analysis")
    st.markdown(
        "**Within-Band Position** shows where an employee's salary sits within their compensation band, "
        "expressed as a percentage from 0% (band minimum) to 100% (band maximum). "
        "Employees below 0% are **Green-Circled** (underpaid below the band minimum); "
        "those above 100% are **Red-Circled** (paid above the band ceiling)."
    )

    df = _load_within_band_records()
    if not df.empty:
        if selected_role != "All":
            df = df[df["_role_id"] == selected_role]
        if selected_level != "All":
            df = df[df["_level_id"] == selected_level]
        if selected_location != "All":
            df = df[df["_location_id"] == selected_location]

    if df.empty:
        st.warning("No records found for within-band position analysis.")
        return

    green_circled = int((df["_raw_zone"] == "GREEN_CIRCLED").sum())
    red_circled = int((df["_raw_zone"] == "RED_CIRCLED").sum())
    in_band = len(df) - (green_circled + red_circled)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Median Band Placement", f"{df['Position (%)'].median():.1f}%")
    col2.metric("Within Band (0% – 100%)", f"{in_band:,} ({in_band/len(df)*100:.1f}%)")
    with col3:
        st.metric("Green-Circled (< 0%)", f"{green_circled:,}")
        st.markdown(
            '<span style="color:#2ecc71; font-size:0.82rem; font-weight:600; border-left:3px solid #2ecc71; padding-left:6px;">Underpaid below minimum</span>',
            unsafe_allow_html=True,
        )
    with col4:
        st.metric("Red-Circled (> 100%)", f"{red_circled:,}")
        st.markdown(
            '<span style="color:#e74c3c; font-size:0.82rem; font-weight:600; border-left:3px solid #e74c3c; padding-left:6px;">Above band ceiling</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    df_chart = df[(df["Position (%)"] >= -100.0) & (df["Position (%)"] <= 200.0)].copy()
    extreme_count = len(df) - len(df_chart)
    if extreme_count > 0:
        st.caption(
            f"Scatter plot focused on -100% to 200% for clarity ({extreme_count} extreme exception record(s) outside this range appear in metrics and the outliers table)."
        )

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        zone_counts = df["Band Zone"].value_counts().reset_index()
        zone_counts.columns = ["Band Zone", "Count"]
        fig_pie = px.pie(
            zone_counts,
            names="Band Zone",
            values="Count",
            title="Workforce Placement Across Band Zones",
            color="Band Zone",
            color_discrete_map=_ZONE_COLORS,
            category_orders={"Band Zone": list(_ZONE_COLORS.keys())},
        )
        apply_clean_layout(fig_pie, legend_bottom=True, height=470, legend_position="bottom")
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_chart2:
        fig_scatter = px.scatter(
            df_chart,
            x="Position (%)",
            y="Salary (USD)",
            color="Band Zone",
            color_discrete_map=_ZONE_COLORS,
            category_orders={"Band Zone": list(_ZONE_COLORS.keys())},
            hover_data=["Employee ID", "Name", "Role", "Level", "Location"],
            title="Salary vs Within-Band Percentage"
        )
        fig_scatter.add_vline(
            x=0.0, line_dash="dash", line_color="#2ecc71",
            annotation_text="Band Min (0%)", annotation_position="top left", annotation_yshift=-6
        )
        fig_scatter.add_vline(
            x=100.0, line_dash="dash", line_color="#e74c3c",
            annotation_text="Band Max (100%)", annotation_position="top right", annotation_yshift=-6
        )
        apply_clean_layout(fig_scatter, legend_bottom=True, height=470)
        st.plotly_chart(fig_scatter, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Range Outliers: Green-Circled & Red-Circled Employees")
    outliers_raw = df[df["_raw_zone"].isin(["GREEN_CIRCLED", "RED_CIRCLED"])].copy()
    if outliers_raw.empty:
        st.success("No Green-Circled or Red-Circled range outliers found under the current filters.")
    else:
        st.caption(f"{len(outliers_raw):,} range outlier record(s) found")
        outliers_disp = pd.DataFrame({
            "Employee ID": outliers_raw["Employee ID"],
            "Employee Name": outliers_raw["Name"],
            "Band Zone": outliers_raw["Band Zone"],
            "Position (%)": outliers_raw["Position (%)"].map(lambda v: fmt_pct(v, 1)),
            "Salary (USD)": outliers_raw["Salary (USD)"].map(fmt_usd),
            "Band Min (USD)": outliers_raw["Band Min (USD)"].map(fmt_usd),
            "Band Max (USD)": outliers_raw["Band Max (USD)"].map(fmt_usd),
            "Role": outliers_raw["Role"],
            "Level": outliers_raw["Level"],
            "Location": outliers_raw["Location"],
        })
        st.dataframe(outliers_disp, use_container_width=True, hide_index=True)
