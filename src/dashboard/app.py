"""
Main Streamlit Application for Compensation Equity and Disparity Analysis System.
Hosts 13 interactive sections covering executive overviews, analytical deep dives,
edge case diagnostics, proposal workflows, audit trails, and ground-truth evaluations.
"""
import sys
from pathlib import Path

# ── Ensure project root is on sys.path before any src.* imports ──────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Set page config (must be the first Streamlit call)
st.set_page_config(
    page_title="Compensation Equity & Disparity System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
def load_css():
    css_path = Path(__file__).parent / "static" / "custom.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Inline fallback styles
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ── View imports ──────────────────────────────────────────────────────────────
from src.database.session import SessionLocal
from src.database.models import Role, Level, Location
from src.dashboard.views import (
    executive_overview,
    employee_analytics,
    band_analysis,
    compa_ratio_view,
    within_band_view,
    disparity_view,
    comparable_groups_view,
    exceptions_view,
    proposals_view,
    approval_history_view,
    audit_trail_view,
    validation_view,
    evaluation_view,
)


# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    db = SessionLocal()
    try:
        # Sidebar Header
        st.sidebar.title("⚖️ CompEquity AI")
        st.sidebar.markdown("**Disparity Analysis & Remediation**")
        st.sidebar.markdown("---")

        # Global Filters
        st.sidebar.subheader("Navigation & Filters")

        roles = [r.role_id for r in db.query(Role.role_id).order_by(Role.role_id).all()]
        levels = [l.level_id for l in db.query(Level.level_id).order_by(Level.rank).all()]
        locations = [loc.location_id for loc in db.query(Location.location_id).order_by(Location.location_id).all()]

        selected_role = st.sidebar.selectbox("Filter Role:", ["All"] + roles, index=0)
        selected_level = st.sidebar.selectbox("Filter Career Level:", ["All"] + levels, index=0)
        selected_location = st.sidebar.selectbox("Filter Location:", ["All"] + locations, index=0)

        st.sidebar.markdown("---")

        # 13 Required Views
        view_options = [
            "1. Executive Overview",
            "2. Employee & Salary Analytics",
            "3. Compensation Band Analysis",
            "4. Compa-Ratio Analysis",
            "5. Within-Band Position Analysis",
            "6. Disparity Detection",
            "7. Comparable Employee Groups",
            "8. Exceptions & Negative Scenarios",
            "9. Adjustment Proposals",
            "10. Approval History",
            "11. Audit Trail Ledger",
            "12. Data Quality & Validation",
            "13. Ground-Truth Evaluation",
        ]

        choice = st.sidebar.radio("Select View:", view_options, index=0)

        # Route to views
        if choice.startswith("1."):
            executive_overview.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("2."):
            employee_analytics.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("3."):
            band_analysis.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("4."):
            compa_ratio_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("5."):
            within_band_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("6."):
            disparity_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("7."):
            comparable_groups_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("8."):
            exceptions_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("9."):
            proposals_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("10."):
            approval_history_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("11."):
            audit_trail_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("12."):
            validation_view.render(db, selected_role, selected_level, selected_location)
        elif choice.startswith("13."):
            evaluation_view.render(db, selected_role, selected_level, selected_location)

    finally:
        db.close()


if __name__ == "__main__":
    main()
