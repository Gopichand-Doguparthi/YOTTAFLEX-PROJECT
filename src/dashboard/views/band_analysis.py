"""
View 3: Compensation Band Analysis.
Visualizes salary band structures, minimum/midpoint/maximum spreads, and effective-dated validity.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import CompensationBand
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    PLOTLY_CONFIG, apply_clean_layout,
)


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compensation Band Structure & Range Analysis")
    st.markdown("Audits effective-dated salary ranges establishing market minimum, midpoint, and maximum bounds (USD-normalized for cross-region comparison).")

    role_map = get_role_map(db)
    level_map = get_level_map(db)
    loc_map = get_location_map(db)
    curr_norm = get_currency_normalizer(db)

    year_filter = st.selectbox("Effective Band Calendar Year:", [2026, 2025, 2024], index=0)

    query = db.query(CompensationBand).filter(
        CompensationBand.effective_start_date >= f"{year_filter}-01-01",
        CompensationBand.effective_start_date <= f"{year_filter}-12-31"
    )

    if selected_role != "All":
        query = query.filter(CompensationBand.role_id == selected_role)
    if selected_level != "All":
        query = query.filter(CompensationBand.level_id == selected_level)
    if selected_location != "All":
        query = query.filter(CompensationBand.location_id == selected_location)

    bands = query.all()

    if not bands:
        st.info("No compensation bands found for the selected criteria.")
        return

    rows = []
    for b in bands:
        min_usd, mid_usd, max_usd = get_band_usd_amounts(b, curr_norm)
        rows.append({
            "Band ID": b.band_id,
            "Role": role_map.get(b.role_id, b.role_id),
            "Level": level_map.get(b.level_id, b.level_id),
            "Location": loc_map.get(b.location_id, b.location_id),
            "Currency": b.currency,
            "Min (USD)": min_usd,
            "Midpoint (USD)": mid_usd,
            "Max (USD)": max_usd,
            "Min (Local)": float(b.min_salary),
            "Midpoint (Local)": float(b.mid_salary),
            "Max (Local)": float(b.max_salary),
            "Spread ($ USD)": round(max_usd - min_usd, 0),
            "Spread (%)": round(((b.max_salary - b.min_salary) / b.min_salary) * 100, 1) if b.min_salary else 0.0,
            "Status": b.status,
        })

    band_df = pd.DataFrame(rows)

    col1, col2, col3 = st.columns(3)
    col1.metric("Bands Analyzed", f"{len(band_df):,}")
    col2.metric("Average Midpoint (USD)", f"${band_df['Midpoint (USD)'].mean():,.0f}")
    col3.metric("Average Spread %", f"{band_df['Spread (%)'].mean():.1f}%")

    st.markdown("---")

    st.subheader(f"Compensation Band Range Spreads — USD Normalized ({year_filter})")
    sample_bands = band_df.head(20).copy()
    sample_bands["Band Label"] = (
        sample_bands["Role"] + " | " + sample_bands["Level"] + " | " + sample_bands["Location"]
    )

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
    apply_clean_layout(fig, legend_bottom=True, height=500, xaxis_tickangle=-35, extra_bottom_margin=60)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Compensation Bands Directory")
    st.dataframe(
        band_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Min (USD)": st.column_config.NumberColumn("Min (USD)", format="$%,.0f"),
            "Midpoint (USD)": st.column_config.NumberColumn("Midpoint (USD)", format="$%,.0f"),
            "Max (USD)": st.column_config.NumberColumn("Max (USD)", format="$%,.0f"),
            "Min (Local)": st.column_config.NumberColumn("Min (Local)", format="%,.0f"),
            "Midpoint (Local)": st.column_config.NumberColumn("Midpoint (Local)", format="%,.0f"),
            "Max (Local)": st.column_config.NumberColumn("Max (Local)", format="%,.0f"),
            "Spread ($ USD)": st.column_config.NumberColumn("Spread ($ USD)", format="$%,.0f"),
            "Spread (%)": st.column_config.NumberColumn("Spread (%)", format="%.1f%%"),
        },
    )
