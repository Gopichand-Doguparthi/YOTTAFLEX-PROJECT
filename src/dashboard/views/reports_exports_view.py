"""
View: Reports & Exports Center.
Generates real-time downloadable CSV and JSON analytical reports from the active database.
"""
import json
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import Employee, SalaryRecord, CompensationBand, AdjustmentProposal
from src.evaluation.evaluator import EvaluationEngine
from src.dashboard.views.helpers import get_band_usd_amounts, load_fx_rates_list


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Reports & Compliance Exports")
    st.markdown("Download live CSV and JSON analytical datasets generated directly from the active compensation database.")

    fx_list = load_fx_rates_list()
    emp_q = db.query(Employee)
    if selected_role != "All":
        emp_q = emp_q.filter(Employee.current_role_id == selected_role)
    if selected_level != "All":
        emp_q = emp_q.filter(Employee.current_level_id == selected_level)
    if selected_location != "All":
        emp_q = emp_q.filter(Employee.current_location_id == selected_location)
    employees = emp_q.all()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Employee Compensation Snapshot (CSV)")
        st.caption(f"Filtered cohort size: {len(employees):,} employees")
        if st.button("Prepare Employee Compensation CSV", key="rep_emp_btn"):
            latest_sals = {}
            for s in db.query(SalaryRecord).all():
                if s.employee_id not in latest_sals or s.effective_date > latest_sals[s.employee_id].effective_date:
                    latest_sals[s.employee_id] = s
            rows = []
            for e in employees:
                sal = latest_sals.get(e.employee_id)
                rows.append({
                    "employee_id": e.employee_id,
                    "name": f"{e.first_name} {e.last_name}",
                    "department": e.department,
                    "role_id": e.current_role_id,
                    "level_id": e.current_level_id,
                    "location_id": e.current_location_id,
                    "fte": e.fte,
                    "normalized_salary_usd": sal.normalized_salary if sal else None,
                    "effective_date": str(sal.effective_date) if sal else None,
                })
            csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
            st.download_button("Download employee_compensation_report.csv", csv_bytes, "employee_compensation_report.csv", "text/csv")

        st.subheader("2. Adjustment Proposals Register (CSV)")
        props = db.query(AdjustmentProposal).all()
        st.caption(f"Total proposals in ledger: {len(props):,}")
        prop_rows = [
            {
                "proposal_id": p.proposal_id,
                "employee_id": p.employee_id,
                "current_salary": p.current_salary,
                "proposed_salary": p.proposed_salary,
                "adjustment_amount": p.adjustment_amount,
                "adjustment_percentage": p.adjustment_percentage,
                "reason_code": p.reason_code,
                "approval_status": p.approval_status,
                "created_by": p.created_by,
                "reviewed_by": p.reviewed_by,
            }
            for p in props
        ]
        st.download_button(
            "Download adjustment_proposals_report.csv",
            pd.DataFrame(prop_rows).to_csv(index=False).encode("utf-8"),
            "adjustment_proposals_report.csv",
            "text/csv",
        )

    with col2:
        st.subheader("3. Active Compensation Bands in USD (CSV)")
        active_bands = db.query(CompensationBand).filter(CompensationBand.status == "ACTIVE").all()
        st.caption(f"Active bands: {len(active_bands):,}")
        if st.button("Prepare Active Bands USD CSV", key="rep_band_btn"):
            b_rows = []
            for b in active_bands:
                usd_min, usd_mid, usd_max = get_band_usd_amounts(b, fx_list)
                b_rows.append({
                    "band_id": b.band_id,
                    "role_id": b.role_id,
                    "level_id": b.level_id,
                    "location_id": b.location_id,
                    "local_currency": b.currency,
                    "local_mid": b.mid_salary,
                    "usd_min": usd_min,
                    "usd_mid": usd_mid,
                    "usd_max": usd_max,
                })
            st.download_button(
                "Download compensation_bands_usd.csv",
                pd.DataFrame(b_rows).to_csv(index=False).encode("utf-8"),
                "compensation_bands_usd.csv",
                "text/csv",
            )

        st.subheader("4. Model Evaluation Metrics Report (JSON)")
        if st.button("Generate Live Evaluation JSON", key="rep_eval_btn"):
            with st.spinner("Evaluating detection engine against ground truth..."):
                eval_res = EvaluationEngine.evaluate(db)
            st.download_button(
                "Download evaluation_report.json",
                json.dumps(eval_res, indent=2, default=str).encode("utf-8"),
                "evaluation_report.json",
                "application/json",
            )
