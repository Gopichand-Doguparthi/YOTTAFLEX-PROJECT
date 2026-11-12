"""
View 3: Compensation Band Analysis.
Visualizes salary band structures, minimum/midpoint/maximum progression by career level,
and horizontal range spreads.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import CompensationBand
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts, load_reference_catalogs,
    fmt_usd, fmt_num, fmt_pct, format_currency_label,
    PLOTLY_CONFIG, apply_clean_layout, build_table_column_config,
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

    catalog = load_reference_catalogs()
    role_map = catalog["role_map"]
    level_map = catalog["level_map"]
    loc_map = catalog["loc_map"]
    level_rank_map = {lid: rank for lid, _, _, rank in catalog["levels_list"]}
    curr_norm = get_currency_normalizer(db)

    yf_col, bf1, bf2 = st.columns(3)
    with yf_col:
        year_filter = st.selectbox("Effective Band Calendar Year:", [2026, 2025, 2024], index=0)

    all_bands = _load_bands_for_year(year_filter)
    with bf1:
        curr_codes = sorted({b["currency"] for b in all_bands})
        curr_label_map = {format_currency_label(c): c for c in curr_codes}
        curr_opts = ["All Currencies"] + list(curr_label_map.keys())
        curr_filter_label = st.selectbox("Filter by Local Currency:", curr_opts, index=0)
        curr_filter = "All Currencies" if curr_filter_label == "All Currencies" else curr_label_map[curr_filter_label]
    with bf2:
        band_status_filter = st.selectbox("Filter by Band Status:", ["All Statuses", "Active", "Expired"], index=0)

    bands = [
        b for b in all_bands
        if (selected_role == "All" or b["role_id"] == selected_role)
        and (selected_level == "All" or b["level_id"] == selected_level)
        and (selected_location == "All" or b["location_id"] == selected_location)
        and (curr_filter == "All Currencies" or b["currency"] == curr_filter)
        and (band_status_filter == "All Statuses" or b["status"].title() == band_status_filter)
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
        short_city = loc_name.split(",")[0]

        raw_rows.append({
            "Level": level_name,
            "Rank": level_rank_map.get(b["level_id"], 99),
            "Short Label": f"{role_name} ({level_name.split('(')[-1].rstrip(')')} · {short_city})",
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

    col_left, col_right = st.columns(2)

    with col_left:
        # Chart 1: Career Level Progression (Min / Midpoint / Max USD)
        lvl_summary = (
            raw_df.groupby(["Rank", "Level"])[["Min (USD)", "Midpoint (USD)", "Max (USD)"]]
            .mean()
            .reset_index()
            .sort_values("Rank")
        )
        max_lvl_val = float(lvl_summary["Max (USD)"].max()) if not lvl_summary.empty else 100000.0

        fig_lvl = go.Figure()
        for col_name, color in [
            ("Min (USD)", "#3b82f6"),
            ("Midpoint (USD)", "#22c55e"),
            ("Max (USD)", "#f97316"),
        ]:
            fig_lvl.add_trace(go.Bar(
                name=col_name.replace(" (USD)", ""),
                x=lvl_summary["Level"],
                y=lvl_summary[col_name],
                text=[f"${v/1000:,.0f}k" for v in lvl_summary[col_name]],
                textposition="outside",
                cliponaxis=False,
                marker_color=color,
                hovertemplate="%{x}<br>" + col_name + ": $%{y:,.0f}<extra></extra>",
            ))
        fig_lvl.update_layout(
            barmode="group",
            title=f"Salary Band Progression by Career Level ({year_filter})",
            xaxis_title="Career Level",
            yaxis_title="Average Annual Salary (USD)",
            yaxis=dict(range=[0, max_lvl_val * 1.20]),
        )
        apply_clean_layout(fig_lvl, legend_bottom=True, height=470, xaxis_tickangle=-20)
        st.plotly_chart(fig_lvl, use_container_width=True, config=PLOTLY_CONFIG)

    with col_right:
        # Chart 2: Horizontal Dumbbell Range Chart for top 10 matching bands
        sample_bands = raw_df.sort_values(["Rank", "Midpoint (USD)"]).head(10).iloc[::-1]

        fig_range = go.Figure()
        for _, row in sample_bands.iterrows():
            fig_range.add_trace(go.Scatter(
                x=[row["Min (USD)"], row["Max (USD)"]],
                y=[row["Short Label"], row["Short Label"]],
                mode="lines",
                line=dict(color="#64748b", width=4),
                showlegend=False,
                hoverinfo="skip",
            ))

        for col_name, color, label in [
            ("Min (USD)", "#3b82f6", "Minimum"),
            ("Midpoint (USD)", "#22c55e", "Midpoint"),
            ("Max (USD)", "#f97316", "Maximum"),
        ]:
            fig_range.add_trace(go.Scatter(
                name=label,
                x=sample_bands[col_name],
                y=sample_bands["Short Label"],
                mode="markers+text" if col_name == "Midpoint (USD)" else "markers",
                text=[f"${v/1000:,.0f}k" for v in sample_bands[col_name]] if col_name == "Midpoint (USD)" else None,
                textposition="top center",
                marker=dict(color=color, size=11, line=dict(color="#0f172a", width=1.5)),
                hovertemplate="%{y}<br>" + label + ": $%{x:,.0f}<extra></extra>",
            ))

        fig_range.update_layout(
            title=f"Band Range Span: Min – Midpoint – Max ({year_filter})",
            xaxis_title="Annual Salary (USD)",
            yaxis_title="",
        )
        apply_clean_layout(fig_range, legend_bottom=True, height=470)
        st.plotly_chart(fig_range, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Compensation Bands Directory")
    band_disp_df = pd.DataFrame(display_rows)
    st.dataframe(
        band_disp_df,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(band_disp_df),
    )
