"""
View 3: Compensation Band Analysis.
Visualizes salary band structures, minimum/midpoint/maximum spreads, and effective-dated validity.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import CompensationBand
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    fmt_usd, fmt_num, fmt_pct, PLOTLY_CONFIG, apply_clean_layout,
)


@st.cache_data(ttl=120, show_spinner=False)
def _load_bands_for_year(year_filter: int) -> list:
    db = SessionLocal()
    try:
        rows = db.query(
            CompensationBand.band_id,
            CompensationBand.role_id,
            CompensationBand.level_id,
            CompensationBand.location_id,
            CompensationBand.currency,
            CompensationBand.min_salary,
            CompensationBand.mid_salary,
            CompensationBand.max_salary,
            CompensationBand.effective_start_date,
            CompensationBand.status,
        ).filter(
            CompensationBand.effective_start_date >= f"{year_filter}-01-01",
            CompensationBand.effective_start_date <= f"{year_filter}-12-31"
        ).all()
        return [
            {
                "band_id": r[0],
                "role_id": r[1],
                "level_id": r[2],
                "location_id": r[3],
                "currency": r[4],
                "min_salary": float(r[5]),
                "mid_salary": float(r[6]),
                "max_salary": float(r[7]),
                "effective_start_date": r[8],
                "status": r[9],
            }
            for r in rows
        ]
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compensation Band Structure & Range Analysis")
    st.markdown("Audits effective-dated salary ranges establishing market minimum, midpoint, and maximum bounds (USD-normalized for cross-region comparison).")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)
    curr_norm = get_currency_normalizer(db)

    year_filter = st.selectbox("Effective Band Calendar Year:", [2026, 2025, 2024], index=0)

    all_bands = _load_bands_for_year(year_filter)
    bands = [
        b for b in all_bands
        if (selected_role == "All" or b["role_id"] == selected_role)
        and (selected_level == "All" or b["level_id"] == selected_level)
        and (selected_location == "All" or b["location_id"] == selected_location)
    ]

    if not bands:
        st.info("No compensation bands found for the selected criteria.")
        return

    raw_rows = []
    display_rows = []
    for b in bands:
        min_usd, mid_usd, max_usd = get_band_usd_amounts(b, curr_norm)
        spread_usd = round(max_usd - min_usd, 0)
        spread_pct = round(((b["max_salary"] - b["min_salary"]) / b["min_salary"]) * 100, 1) if b["min_salary"] else 0.0
        role_name = role_map.get(b["role_id"], b["role_id"])
        level_name = level_map.get(b["level_id"], b["level_id"])
        loc_name = loc_map.get(b["location_id"], b["location_id"])

        raw_rows.append({
            "Band Label": f"{role_name} | {level_name} | {loc_name}",
            "Min (USD)": min_usd,
            "Midpoint (USD)": mid_usd,
            "Max (USD)": max_usd,
            "Spread (%)": spread_pct,
        })
        display_rows.append({
            "Band ID": b["band_id"],
            "Role": role_name,
            "Level": level_name,
            "Location": loc_name,
            "Currency": b["currency"],
            "Min (USD)": fmt_usd(min_usd),
            "Midpoint (USD)": fmt_usd(mid_usd),
            "Max (USD)": fmt_usd(max_usd),
            "Min (Local)": fmt_num(b["min_salary"], 0),
            "Midpoint (Local)": fmt_num(b["mid_salary"], 0),
            "Max (Local)": fmt_num(b["max_salary"], 0),
            "Spread (USD)": fmt_usd(spread_usd),
            "Spread (%)": fmt_pct(spread_pct),
            "Status": b["status"].title(),
        })

    raw_df = pd.DataFrame(raw_rows)

    col1, col2, col3 = st.columns(3)
    col1.metric("Bands Analyzed", f"{len(raw_df):,}")
    col2.metric("Average Midpoint (USD)", f"${raw_df['Midpoint (USD)'].mean():,.0f}")
    col3.metric("Average Spread %", f"{raw_df['Spread (%)'].mean():.1f}%")

    st.markdown("---")

    st.subheader(f"Compensation Band Range Spreads — USD Normalized ({year_filter})")
    sample_bands = raw_df.head(20)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Minimum (USD)",
        x=sample_bands["Band Label"],
        y=sample_bands["Min (USD)"],
        marker_color="#3498db",
        hovertemplate="%{x}<br>Min: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Midpoint (USD)",
        x=sample_bands["Band Label"],
        y=sample_bands["Midpoint (USD)"],
        marker_color="#2ecc71",
        hovertemplate="%{x}<br>Midpoint: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Maximum (USD)",
        x=sample_bands["Band Label"],
        y=sample_bands["Max (USD)"],
        marker_color="#e67e22",
        hovertemplate="%{x}<br>Max: $%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        title="Sample Compensation Bands: Minimum, Midpoint, and Maximum Salary Ranges (USD)",
        yaxis_title="Annual Salary (USD)",
        xaxis_title="Role | Career Level | Location",
    )
    apply_clean_layout(fig, legend_bottom=True, height=520, xaxis_tickangle=-35, extra_bottom_margin=70)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Compensation Bands Directory")
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
