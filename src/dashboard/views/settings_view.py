"""
View: System Settings & Governance Thresholds.
Displays and allows session-level inspection of analytical thresholds, database engine, and RBAC rules.
"""
import streamlit as st
from sqlalchemy.orm import Session

from src.config import (
    DATABASE_URL, REPORTING_CURRENCY, RANDOM_SEED,
    COMPA_RATIO_MIN, COMPA_RATIO_MAX,
    DISPARITY_THRESHOLD_PERCENT, PERFORMANCE_EXEMPLARY_RATING,
    MIN_COMPARABLE_GROUP_SIZE,
)
from src.workflow.proposal_manager import ProposalManager


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("System Settings & Governance Configuration")
    st.markdown("Review analytical thresholds, reproducibility parameters, and approval authorization policies.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Reporting Currency", REPORTING_CURRENCY)
    c2.metric("Random Seed", str(RANDOM_SEED))
    c3.metric("Min Peer Cohort Size", str(MIN_COMPARABLE_GROUP_SIZE))

    st.markdown("---")
    st.subheader("Analytical Thresholds (Active Environment)")
    with st.form("settings_preview_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            cr_min = st.number_input("Target Compa-Ratio Min", min_value=0.50, max_value=1.00, value=float(st.session_state.get("cfg_cr_min", COMPA_RATIO_MIN)), step=0.05)
            cr_max = st.number_input("Target Compa-Ratio Max", min_value=1.00, max_value=1.80, value=float(st.session_state.get("cfg_cr_max", COMPA_RATIO_MAX)), step=0.05)
        with col_b:
            disp_pct = st.number_input("Disparity Deviation Threshold (%)", min_value=5.0, max_value=50.0, value=float(st.session_state.get("cfg_disp_pct", DISPARITY_THRESHOLD_PERCENT)), step=1.0)
            perf_min = st.number_input("Exemplary Performance Rating Cutoff", min_value=1.0, max_value=5.0, value=float(st.session_state.get("cfg_perf_min", PERFORMANCE_EXEMPLARY_RATING)), step=0.1)

        if st.form_submit_button("Save Session Preferences"):
            st.session_state["cfg_cr_min"] = cr_min
            st.session_state["cfg_cr_max"] = cr_max
            st.session_state["cfg_disp_pct"] = disp_pct
            st.session_state["cfg_perf_min"] = perf_min
            st.success("Session analytical threshold preferences updated.")

    st.markdown("---")
    st.subheader("Security & Governance Policies")
    st.write(f"- **Database Backend:** `{DATABASE_URL.split('://')[0]}`")
    st.write(f"- **Authorized Approver Roles:** `{', '.join(sorted(ProposalManager.ALLOWED_APPROVER_ROLES))}`")
    st.write("- **Self-Approval Prevention:** Enabled (`created_by != reviewed_by` enforced in `ProposalManager` & `/proposals/{id}/review`).")
    st.write("- **Ground-Truth Isolation:** Enabled (ground truth is excluded from operational detection & exception routes).")
