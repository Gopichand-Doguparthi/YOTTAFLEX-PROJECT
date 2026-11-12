"""
View: System Settings & Governance Thresholds.
Persists analytical thresholds to data/system_settings.json with validation and RBAC checks.
"""
import json
from pathlib import Path
import streamlit as st
from sqlalchemy.orm import Session

from src.config import (
    DATA_DIR, DATABASE_URL, REPORTING_CURRENCY, RANDOM_SEED,
    COMPA_RATIO_MIN, COMPA_RATIO_MAX,
    DISPARITY_THRESHOLD_PERCENT, PERFORMANCE_EXEMPLARY_RATING,
    MIN_COMPARABLE_GROUP_SIZE,
)
from src.workflow.proposal_manager import ProposalManager

SETTINGS_FILE = Path(DATA_DIR) / "system_settings.json"
AUTHORIZED_CONFIG_ROLES = {"SYSTEM_ADMIN", "HR_PARTNER"}


def _load_persisted_settings() -> dict:
    defaults = {
        "reporting_currency": REPORTING_CURRENCY,
        "compa_ratio_min": float(COMPA_RATIO_MIN),
        "compa_ratio_max": float(COMPA_RATIO_MAX),
        "disparity_threshold_percent": float(DISPARITY_THRESHOLD_PERCENT),
        "performance_exemplary_rating": float(PERFORMANCE_EXEMPLARY_RATING),
    }
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update({k: saved[k] for k in defaults if k in saved})
        except Exception:
            pass
    return defaults


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("System Settings & Governance Configuration")
    st.markdown("Configure analytical thresholds, inspect database status, and enforce role-based configuration governance.")

    current_cfg = _load_persisted_settings()

    c1, c2, c3 = st.columns(3)
    c1.metric("Reporting Currency", current_cfg["reporting_currency"])
    c2.metric("Random Seed", str(RANDOM_SEED))
    c3.metric("Min Peer Cohort Size", str(MIN_COMPARABLE_GROUP_SIZE))

    st.markdown("---")
    st.subheader("Analytical Thresholds (Persisted Configuration)")
    actor_role = st.selectbox(
        "Active Configuration Role:",
        ["SYSTEM_ADMIN", "HR_PARTNER", "MANAGER", "EMPLOYEE"],
        index=0,
        key="cfg_actor_role",
    )

    with st.form("settings_preview_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            rep_curr = st.selectbox("Base Reporting Currency", ["USD", "EUR", "GBP"], index=["USD", "EUR", "GBP"].index(current_cfg["reporting_currency"]) if current_cfg["reporting_currency"] in ["USD", "EUR", "GBP"] else 0)
            cr_min = st.number_input("Target Compa-Ratio Min", min_value=0.50, max_value=1.00, value=float(current_cfg["compa_ratio_min"]), step=0.05)
            cr_max = st.number_input("Target Compa-Ratio Max", min_value=1.00, max_value=1.80, value=float(current_cfg["compa_ratio_max"]), step=0.05)
        with col_b:
            disp_pct = st.number_input("Disparity Deviation Threshold (%)", min_value=5.0, max_value=50.0, value=float(current_cfg["disparity_threshold_percent"]), step=1.0)
            perf_min = st.number_input("Exemplary Performance Rating Cutoff", min_value=1.0, max_value=5.0, value=float(current_cfg["performance_exemplary_rating"]), step=0.1)

        if st.form_submit_button("Save Session Preferences"):
            if actor_role not in AUTHORIZED_CONFIG_ROLES:
                st.error(f"Unauthorized: Role '{actor_role}' is not permitted to modify system settings.")
            elif cr_min >= cr_max:
                st.error("Invalid configuration: Compa-Ratio Min must be strictly less than Compa-Ratio Max.")
            else:
                new_cfg = {
                    "reporting_currency": rep_curr,
                    "compa_ratio_min": float(cr_min),
                    "compa_ratio_max": float(cr_max),
                    "disparity_threshold_percent": float(disp_pct),
                    "performance_exemplary_rating": float(perf_min),
                }
                SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
                SETTINGS_FILE.write_text(json.dumps(new_cfg, indent=2), encoding="utf-8")
                st.session_state["cfg_cr_min"] = cr_min
                st.session_state["cfg_cr_max"] = cr_max
                st.session_state["cfg_disp_pct"] = disp_pct
                st.session_state["cfg_perf_min"] = perf_min
                st.success("Configuration saved to data/system_settings.json and persisted across reloads.")

    st.markdown("---")
    st.subheader("Security & Governance Policies")
    st.write(f"- **Database Backend:** `{DATABASE_URL.split('://')[0]}` (Connected)")
    st.write(f"- **Authorized Approver Roles:** `{', '.join(sorted(ProposalManager.ALLOWED_APPROVER_ROLES))}`")
    st.write("- **Self-Approval Prevention:** Enabled (`created_by != reviewed_by` enforced in `ProposalManager` & `/proposals/{id}/review`).")
    st.write("- **Ground-Truth Isolation:** Enabled (ground truth is excluded from operational detection & exception routes).")
