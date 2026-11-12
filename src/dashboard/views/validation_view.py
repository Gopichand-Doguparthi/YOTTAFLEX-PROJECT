"""
View 12: Data Quality & Validation Suite.
Audits database for referential integrity, primary-key uniqueness, arithmetic, and enum checks.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.validation.data_validator import DataValidator
from src.validation.reproducibility import ReproducibilityVerifier
from src.dashboard.views.helpers import build_table_column_config


@st.cache_data(ttl=120, show_spinner=False)
def _run_cached_validation() -> dict:
    db = SessionLocal()
    try:
        return DataValidator.run_all_checks(db)
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Data Quality, Integrity & Reproducibility Suite")
    st.markdown("Validates primary-key uniqueness, foreign-key integrity, enum validity, arithmetic reconciliation, and reproducible data generation.")

    if st.button("Re-run Data Integrity Audit", type="primary"):
        st.cache_data.clear()

    res = _run_cached_validation()

    col1, col2, col3 = st.columns(3)
    col1.metric("Validation Pass Rate", f"{res['pass_rate_pct']}%")
    col2.metric("Total Integrity Checks", res["total_checks"])
    col3.metric("Passed Checks", f"{res['passed_checks']} / {res['total_checks']}")

    st.markdown("---")

    st.subheader("Data Validation Assertions Status")
    val_status_filter = st.selectbox("Filter by Validation Status:", ["All Checks", "PASSED", "FAILED"], index=0)
    detail_data = [
        {
            "Check Name": d["check_name"],
            "Status": "PASSED" if d["passed"] else "FAILED",
            "Violations Count": d["violations_count"],
            "Description": d["description"],
            "Details": "; ".join(d["details"]) if d["details"] else "None (Clean)"
        }
        for d in res["details"]
    ]
    df_val = pd.DataFrame(detail_data)
    if val_status_filter != "All Checks":
        df_val = df_val[df_val["Status"] == val_status_filter]
    st.dataframe(
        df_val,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(df_val),
    )

    st.markdown("---")
    st.subheader("Synthetic Generator Reproducibility Verification")
    st.write("Verifies that running the synthetic data generator twice using seed `20261022` yields identical SHA-256 hashes and row counts.")

    if st.button("Verify Generator Reproducibility"):
        with st.spinner("Running double generation comparison with seed 20261022..."):
            repro = ReproducibilityVerifier.verify(seed=20261022, scale="starter")
            if repro["is_reproducible"]:
                st.success("All 14 generated tables and deterministic IDs are 100% bit-for-bit identical across runs!")
            else:
                st.error("Reproducibility verification failed!")

            repro_df = pd.DataFrame([
                {
                    "Table": k,
                    "Run 1 Rows": v["rows_run1"],
                    "Run 2 Rows": v["rows_run2"],
                    "Hashes Match": "MATCH" if v["is_match"] else "MISMATCH"
                }
                for k, v in repro["table_results"].items()
            ])
            st.dataframe(repro_df, use_container_width=True, hide_index=True)
