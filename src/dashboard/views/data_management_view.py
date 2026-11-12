"""
View: Data Management & Reproducibility Operations.
Displays live database table counts, dataset export manifests, and deterministic reproducibility checks.
"""
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from src.config import DATA_DIR, RANDOM_SEED
from src.database.models import (
    Location, Role, Level, CompensationBand, Employee, SalaryRecord,
    PerformanceEvidence, Tenure, Promotion, AdjustmentProposal,
    ApprovalEvent, ExchangeRate, RoleComparabilityRationale, GroundTruthRecord
)
from src.validation.reproducibility import ReproducibilityVerifier
from src.dashboard.views.helpers import build_table_column_config


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Data Management & Seed Governance")
    st.markdown("Inspect live relational table volumes, dataset export manifests, and deterministic reproducibility.")

    tables = [
        ("Employees", Employee),
        ("Roles", Role),
        ("Levels", Level),
        ("Locations", Location),
        ("Compensation Bands", CompensationBand),
        ("Salary Records", SalaryRecord),
        ("Performance Evidence", PerformanceEvidence),
        ("Tenure Records", Tenure),
        ("Promotions", Promotion),
        ("Adjustment Proposals", AdjustmentProposal),
        ("Approval Events", ApprovalEvent),
        ("Exchange Rates", ExchangeRate),
        ("Role Comparability Rationales", RoleComparabilityRationale),
        ("Ground Truth Records", GroundTruthRecord),
    ]

    counts = [{"Entity": name, "Row Count": db.query(model).count()} for name, model in tables]
    df_counts = pd.DataFrame(counts)

    c1, c2, c3 = st.columns(3)
    c1.metric("Active Tables", len(tables))
    c2.metric("Total Database Rows", f"{int(df_counts['Row Count'].sum()):,}")
    c3.metric("Configured Seed", str(RANDOM_SEED))

    st.markdown("---")
    st.subheader("Live Database Entity Inventory")
    st.dataframe(df_counts, use_container_width=True, hide_index=True, column_config=build_table_column_config(df_counts))

    st.markdown("---")
    st.subheader("Exported Dataset Manifests")
    manifest_cols = st.columns(2)
    for idx, scale in enumerate(["starter", "full"]):
        manifest_path = Path(DATA_DIR) / scale / "manifest.json"
        with manifest_cols[idx]:
            st.markdown(f"**{scale.title()} Dataset (`data/{scale}/`)**")
            if manifest_path.exists():
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                files_meta = data.get("files", {})
                st.caption(f"Tracked files: {len(files_meta)}")
                rows = [
                    {"File": fname, "Rows": meta.get("rows", "—"), "Size (KB)": round(meta.get("size_bytes", 0) / 1024, 1)}
                    for fname, meta in list(files_meta.items())[:12]
                ]
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info(f"No manifest found at `{manifest_path}`.")

    st.markdown("---")
    st.subheader("Deterministic Reproducibility Verification")
    if st.button("Run Starter Reproducibility Check (Seed 20261022)", type="primary"):
        with st.spinner("Running double-pass deterministic generation comparison..."):
            res = ReproducibilityVerifier.verify(seed=RANDOM_SEED, scale="starter")
        if res["is_reproducible"]:
            st.success("100% Reproducible: Both independent runs produced identical row counts and SHA-256 hashes across all 14 tables.")
        else:
            st.error(f"Reproducibility mismatch detected: {res.get('mismatches')}")
        tbl_rows = [
            {
                "Table": tbl,
                "Run 1 Rows": info["rows_run1"],
                "Run 2 Rows": info["rows_run2"],
                "SHA-256 Match": "MATCH" if info["is_match"] else "MISMATCH",
            }
            for tbl, info in res["table_results"].items()
        ]
        st.dataframe(pd.DataFrame(tbl_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Import & Validate Dataset File (CSV / JSON)")
    imp_target = st.selectbox("Target Entity Schema:", ["employees", "salary_records"], key="dm_imp_target")
    uploaded = st.file_uploader("Upload CSV or JSON file for schema & integrity validation:", type=["csv", "json"], key="dm_uploader")
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_up = pd.read_csv(uploaded)
            else:
                df_up = pd.DataFrame(json.load(uploaded))

            required_cols = (
                {"employee_id", "first_name", "last_name", "email", "current_role_id", "current_level_id", "current_location_id", "fte"}
                if imp_target == "employees"
                else {"salary_id", "employee_id", "base_salary", "currency", "fte", "effective_date"}
            )
            missing_cols = sorted(required_cols - set(df_up.columns))
            if missing_cols:
                st.error(f"Validation failed — missing required columns: {missing_cols}")
            elif df_up.empty:
                st.error("Validation failed — uploaded file contains 0 rows.")
            else:
                pk_col = "employee_id" if imp_target == "employees" else "salary_id"
                dups = int(df_up[pk_col].duplicated().sum())
                bad_fte = int(((pd.to_numeric(df_up["fte"], errors="coerce").fillna(-1) <= 0) | (pd.to_numeric(df_up["fte"], errors="coerce").fillna(99) > 1.0)).sum())
                if dups > 0 or bad_fte > 0:
                    st.error(f"Validation failed — {dups} duplicate {pk_col}(s), {bad_fte} invalid FTE value(s) outside (0.0, 1.0].")
                else:
                    st.success(f"Schema & integrity validation passed for {len(df_up):,} `{imp_target}` row(s)!")
        except Exception as exc:
            st.error(f"Rejected invalid file: {exc}")
