"""
Main Streamlit Application for Compensation Equity and Disparity Analysis System.
Hosts 13 interactive sections covering executive overviews, analytical deep dives,
edge case diagnostics, proposal workflows, audit trails, and ground-truth evaluations.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path before any src.* imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Set page config (must be the first Streamlit call)
st.set_page_config(
    page_title="Compensation Equity & Disparity System",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_css():
    css_path = Path(__file__).parent / "static" / "custom.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()

# Sidebar navigation & layout styling
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Sidebar nav buttons — full width, strictly left-aligned */
    [data-testid="stSidebar"] .stButton,
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
        width: 100% !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        background: transparent;
        color: #cbd5e1;
        border: none;
        border-radius: 6px;
        padding: 0.42rem 0.75rem !important;
        margin: 1px 0;
        font-size: 0.875rem;
        font-weight: 400;
        letter-spacing: 0.01em;
        transition: background 0.15s ease, color 0.15s ease, padding-left 0.15s ease;
        cursor: pointer;
    }
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"] > div,
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"] p {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"]:hover {
        background: rgba(99, 102, 241, 0.20) !important;
        color: #ffffff !important;
        padding-left: 1.0rem !important;
    }
    [data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background: rgba(99, 102, 241, 0.34) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-left: 3px solid #818cf8 !important;
    }
    [data-testid="stSidebar"] button[data-testid^="stBaseButton"]:focus {
        box-shadow: none;
        outline: none;
    }

    /* Highlighted, larger section headings in sidebar */
    .nav-section-label {
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f1f5f9;
        background: rgba(99, 102, 241, 0.22);
        border-left: 3px solid #818cf8;
        border-radius: 4px;
        padding: 0.34rem 0.75rem;
        margin: 12px 0 4px 0;
        text-align: left;
    }
</style>
""", unsafe_allow_html=True)

from src.database.session import SessionLocal
from src.dashboard.views.helpers import load_reference_catalogs
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

# Nav items definition (clean left-aligned text, no icons)
NAV_ITEMS = [
    ("overview",     "Executive Overview",          "Overview"),
    ("employee",     "Employee & Salary Analytics", "Analytics"),
    ("band",         "Compensation Band Analysis",  "Analytics"),
    ("compa",        "Compa-Ratio Analysis",        "Analytics"),
    ("within",       "Within-Band Position",        "Analytics"),
    ("disparity",    "Disparity Detection",         "Disparity & Proposals"),
    ("comparable",   "Comparable Employee Groups",  "Disparity & Proposals"),
    ("exceptions",   "Exceptions & Edge Cases",     "Disparity & Proposals"),
    ("proposals",    "Adjustment Proposals",        "Disparity & Proposals"),
    ("approvals",    "Approval History",            "Disparity & Proposals"),
    ("audit",        "Audit Trail Ledger",          "Governance"),
    ("validation",   "Data Quality & Validation",   "Governance"),
    ("evaluation",   "Ground-Truth Evaluation",     "Governance"),
]


def main():
    catalog = load_reference_catalogs()

    # Sidebar Header
    st.sidebar.title("CompEquity AI")
    st.sidebar.markdown("**Disparity Analysis & Remediation**")
    st.sidebar.markdown("---")

    # Global Filters (cached catalogs)
    st.sidebar.subheader("Filters")

    role_options = ["All"] + [title for _, title in catalog["roles_list"]]
    role_id_map = {**{"All": "All"}, **{title: rid for rid, title in catalog["roles_list"]}}
    selected_role_label = st.sidebar.selectbox("Filter Role:", role_options, index=0)
    selected_role = role_id_map[selected_role_label]

    level_options = ["All"] + [f"{name} ({code})" for _, name, code, _ in catalog["levels_list"]]
    level_id_map = {**{"All": "All"}, **{f"{name} ({code})": lid for lid, name, code, _ in catalog["levels_list"]}}
    selected_level_label = st.sidebar.selectbox("Filter Career Level:", level_options, index=0)
    selected_level = level_id_map[selected_level_label]

    loc_options = ["All"] + [name for _, name in catalog["locs_list"]]
    loc_id_map = {**{"All": "All"}, **{name: loc_id for loc_id, name in catalog["locs_list"]}}
    selected_loc_label = st.sidebar.selectbox("Filter Location:", loc_options, index=0)
    selected_location = loc_id_map[selected_loc_label]

    st.sidebar.markdown("---")

    # Navigation
    if "active_view" not in st.session_state:
        st.session_state.active_view = "overview"

    current_section = None
    for key, label, section in NAV_ITEMS:
        if section != current_section:
            st.sidebar.markdown(f'<div class="nav-section-label">{section}</div>', unsafe_allow_html=True)
            current_section = section

        btn_type = "primary" if st.session_state.active_view == key else "secondary"
        if st.sidebar.button(label, key=f"nav_{key}", type=btn_type, use_container_width=True):
            st.session_state.active_view = key
            st.rerun()

    # Route to active view
    db = SessionLocal()
    try:
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
