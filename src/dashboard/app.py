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

# Inject nav-button styles + page chrome
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* ── Sidebar nav buttons ── */
    div[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left !important;
        background: transparent;
        color: #cbd5e1;
        border: none;
        border-radius: 6px;
        padding: 0.42rem 0.9rem;
        margin: 1px 0;
        font-size: 0.88rem;
        font-weight: 400;
        letter-spacing: 0.01em;
        transition: background 0.15s ease, color 0.15s ease, padding-left 0.15s ease;
        cursor: pointer;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(99, 102, 241, 0.18) !important;
        color: #ffffff !important;
        padding-left: 1.2rem !important;
    }
    div[data-testid="stSidebar"] .stButton > button:focus {
        box-shadow: none;
        outline: none;
    }
    /* Active nav item highlight (injected via markdown) */
    .nav-active button {
        background: rgba(99, 102, 241, 0.35) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-left: 3px solid #818cf8 !important;
    }

    /* ── Section dividers in sidebar ── */
    .nav-section-label {
        font-size: 0.70rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #64748b;
        padding: 0.6rem 0.9rem 0.2rem 0.9rem;
        margin-top: 4px;
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

# ── Nav items definition ──────────────────────────────────────────────────────
NAV_ITEMS = [
    # (key, label, icon, section)
    ("overview",     "Executive Overview",         "🏠", "Overview"),
    ("employee",     "Employee & Salary Analytics","👥", "Analytics"),
    ("band",         "Compensation Band Analysis", "📊", "Analytics"),
    ("compa",        "Compa-Ratio Analysis",       "📐", "Analytics"),
    ("within",       "Within-Band Position",       "🎯", "Analytics"),
    ("disparity",    "Disparity Detection",        "⚠️", "Disparity & Proposals"),
    ("comparable",   "Comparable Employee Groups", "🔗", "Disparity & Proposals"),
    ("exceptions",   "Exceptions & Edge Cases",    "🚨", "Disparity & Proposals"),
    ("proposals",    "Adjustment Proposals",       "📝", "Disparity & Proposals"),
    ("approvals",    "Approval History",           "✅", "Disparity & Proposals"),
    ("audit",        "Audit Trail Ledger",         "📋", "Governance"),
    ("validation",   "Data Quality & Validation",  "🔍", "Governance"),
    ("evaluation",   "Ground-Truth Evaluation",    "🏆", "Governance"),
]

# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    db = SessionLocal()
    try:
        # ── Sidebar ──
        st.sidebar.title("⚖️ CompEquity AI")
        st.sidebar.markdown("**Disparity Analysis & Remediation**")
        st.sidebar.markdown("---")

        # ── Global Filters ──
        st.sidebar.subheader("Filters")

        # Role filter — show human-readable titles
        all_roles = db.query(Role.role_id, Role.role_title).order_by(Role.role_title).all()
        role_options = ["All"] + [f"{r.role_title}" for r in all_roles]
        role_id_map  = {"All": "All"} | {r.role_title: r.role_id for r in all_roles}
        selected_role_label = st.sidebar.selectbox("Filter Role:", role_options, index=0)
        selected_role = role_id_map[selected_role_label]

        # Level filter
        levels = db.query(Level.level_id, Level.level_name).order_by(Level.rank).all()
        level_options = ["All"] + [f"{l.level_name} ({l.level_id})" for l in levels]
        level_id_map  = {"All": "All"} | {f"{l.level_name} ({l.level_id})": l.level_id for l in levels}
        selected_level_label = st.sidebar.selectbox("Filter Career Level:", level_options, index=0)
        selected_level = level_id_map[selected_level_label]

        # Location filter — show full city names
        locs = db.query(Location.location_id, Location.location_name).order_by(Location.location_name).all()
        loc_options = ["All"] + [f"{loc.location_name}" for loc in locs]
        loc_id_map  = {"All": "All"} | {loc.location_name: loc.location_id for loc in locs}
        selected_loc_label = st.sidebar.selectbox("Filter Location:", loc_options, index=0)
        selected_location = loc_id_map[selected_loc_label]

        st.sidebar.markdown("---")

        # ── Navigation ──
        if "active_view" not in st.session_state:
            st.session_state.active_view = "overview"

        st.sidebar.markdown("**Navigation**")

        current_section = None
        for key, label, icon, section in NAV_ITEMS:
            # Print section header when section changes
            if section != current_section:
                st.sidebar.markdown(f'<div class="nav-section-label">{section}</div>', unsafe_allow_html=True)
                current_section = section

            if st.sidebar.button(f"{icon}  {label}", key=f"nav_{key}"):
                st.session_state.active_view = key

        # ── Route to active view ──
        view = st.session_state.active_view
        dispatch = {
            "overview":    lambda: executive_overview.render(db, selected_role, selected_level, selected_location),
            "employee":    lambda: employee_analytics.render(db, selected_role, selected_level, selected_location),
            "band":        lambda: band_analysis.render(db, selected_role, selected_level, selected_location),
            "compa":       lambda: compa_ratio_view.render(db, selected_role, selected_level, selected_location),
            "within":      lambda: within_band_view.render(db, selected_role, selected_level, selected_location),
            "disparity":   lambda: disparity_view.render(db, selected_role, selected_level, selected_location),
            "comparable":  lambda: comparable_groups_view.render(db, selected_role, selected_level, selected_location),
            "exceptions":  lambda: exceptions_view.render(db, selected_role, selected_level, selected_location),
            "proposals":   lambda: proposals_view.render(db, selected_role, selected_level, selected_location),
            "approvals":   lambda: approval_history_view.render(db, selected_role, selected_level, selected_location),
            "audit":       lambda: audit_trail_view.render(db, selected_role, selected_level, selected_location),
            "validation":  lambda: validation_view.render(db, selected_role, selected_level, selected_location),
            "evaluation":  lambda: evaluation_view.render(db, selected_role, selected_level, selected_location),
        }
        dispatch.get(view, dispatch["overview"])()

    finally:
        db.close()


if __name__ == "__main__":
    main()
