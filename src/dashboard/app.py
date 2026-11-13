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
import streamlit.components.v1 as components

# Set page config (must be the first Streamlit call)
st.set_page_config(
    page_title="Compensation Equity & Disparity System",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_css():
    css_path = Path(__file__).parent / "static" / "custom.css"
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()

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
    data_management_view,
    reports_exports_view,
    settings_view,
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
    ("approvals",    "Approvals & Review Queue",    "Disparity & Proposals"),
    ("audit",        "Audit Trail Ledger",          "Governance"),
    ("data_mgmt",    "Data Management",             "Governance"),
    ("reports",      "Reports & Exports",           "Governance"),
    ("validation",   "Data Quality & Validation",   "Governance"),
    ("evaluation",   "Ground-Truth Evaluation",     "Governance"),
    ("settings",     "Settings",                    "Governance"),
]


def ensure_database_ready():
    """Auto-initializes tables and loads full dataset (5,000 employees) if deploying to an environment without an existing DB."""
    try:
        import os
        from sqlalchemy import inspect
        from src.database.session import engine, init_db, SessionLocal
        from src.database.models import Role, Employee
        inspector = inspect(engine)
        if not inspector.has_table("roles"):
            init_db()
        db = SessionLocal()
        role_count = db.query(Role).count()
        emp_count = db.query(Employee).count() if inspector.has_table("employees") else 0
        db.close()

        target_scale = os.getenv("DATASET_SCALE", "full")

        # If empty or if currently only has starter dataset (100) and target is full (5,000)
        if role_count == 0 or (target_scale == "full" and emp_count < 5000):
            from src.generator.synthetic_generator import SyntheticDataGenerator
            from scripts.run_generator import load_dataset_into_db
            from src.config import RANDOM_SEED
            data = SyntheticDataGenerator(seed=RANDOM_SEED, scale=target_scale).generate_all()
            load_dataset_into_db(data)
    except Exception as e:
        st.warning(f"Database readiness notice: {e}")


def main():
    ensure_database_ready()
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
            st.sidebar.markdown(
                f'<div class="nav-section-label">{section}</div>'
                f'<div style="height:10px;line-height:10px;font-size:1px;">&nbsp;</div>',
                unsafe_allow_html=True,
            )
            current_section = section

        btn_type = "primary" if st.session_state.active_view == key else "secondary"
        if st.sidebar.button(label, key=f"nav_{key}", type=btn_type, use_container_width=True):
            st.session_state.active_view = key
            st.session_state["scroll_to_top"] = True
            st.rerun()

    if st.session_state.pop("scroll_to_top", False):
        components.html(
            """
            <script>
                (function() {
                    const targets = [
                        window.parent.document.querySelector('section.main'),
                        window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
                        window.parent.document.documentElement,
                        window.parent
                    ];
                    targets.forEach(function(el) {
                        if (el && typeof el.scrollTo === 'function') {
                            el.scrollTo({ top: 0, behavior: 'instant' });
                        }
                    });
                })();
            </script>
            """,
            height=0,
        )

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
            "data_mgmt":   lambda: data_management_view.render(db, selected_role, selected_level, selected_location),
            "reports":     lambda: reports_exports_view.render(db, selected_role, selected_level, selected_location),
            "validation":  lambda: validation_view.render(db, selected_role, selected_level, selected_location),
            "evaluation":  lambda: evaluation_view.render(db, selected_role, selected_level, selected_location),
            "settings":    lambda: settings_view.render(db, selected_role, selected_level, selected_location),
        }
        dispatch.get(view, dispatch["overview"])()
    finally:
        db.close()


if __name__ == "__main__":
    main()
