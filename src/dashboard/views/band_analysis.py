"""
View 3: Compensation Band Analysis.
Visualizes salary band structures, minimum/midpoint/maximum spreads, and effective-dated validity.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import CompensationBand, Role, Level, Location


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compensation Band Structure & Range Analysis")
    st.markdown("Audits effective-dated salary ranges establishing market minimum, midpoint, and maximum bounds.")

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

    band_df = pd.DataFrame([
        {
            "Band ID": b.band_id,
            "Role": b.role_id,
            "Level": b.level_id,
            "Location": b.location_id,
            "Currency": b.currency,
            "Min Salary": b.min_salary,
            "Midpoint Salary": b.mid_salary,
            "Max Salary": b.max_salary,
            "Spread ($)": b.max_salary - b.min_salary,
            "Spread (%)": round(((b.max_salary - b.min_salary) / b.min_salary) * 100, 1),
            "Status": b.status
        }
        for b in bands
    ])

    col1, col2, col3 = st.columns(3)
    col1.metric("Bands Analyzed", len(band_df))
    col2.metric("Average Midpoint", f"${band_df['Midpoint Salary'].mean():,.0f}")
    col3.metric("Average Spread %", f"{band_df['Spread (%)'].mean():.1f}%")

    st.markdown("---")

    # Range comparison bar chart
    st.subheader(f"Compensation Band Range Spreads ({year_filter})")
    sample_bands = band_df.head(25)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Minimum",
        x=sample_bands["Band ID"],
        y=sample_bands["Min Salary"],
        marker_color="#3498db"
    ))
    fig.add_trace(go.Bar(
        name="Midpoint",
        x=sample_bands["Band ID"],
        y=sample_bands["Midpoint Salary"],
        marker_color="#2ecc71"
    ))
    fig.add_trace(go.Bar(
        name="Maximum",
        x=sample_bands["Band ID"],
        y=sample_bands["Max Salary"],
        marker_color="#e67e22"
    ))

    fig.update_layout(
        barmode="group",
        title="Sample Compensation Bands: Min, Mid, and Max Salary Ranges",
        xaxis_tickangle=-45,
        yaxis_title="Salary (Local Currency / USD)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Compensation Bands Directory")
    st.dataframe(band_df, use_container_width=True)
