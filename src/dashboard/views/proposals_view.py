"""
View 9: Adjustment Proposals Management.
Enables review and initiation of compensation remediation proposals.
"""
from datetime import date
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal, Employee, SalaryRecord
from src.workflow.proposal_manager import ProposalManager


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compensation Adjustment Proposals")
    st.markdown("Manages equity adjustment proposals, approval workflows, and remediation actions.")

    # Proposal creation form
    with st.expander("Initiate New Compensation Adjustment Proposal"):
        with st.form("new_proposal_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                prop_emp_id = st.text_input("Employee ID (e.g. EMP-000001):")
                proposed_salary = st.number_input("Proposed Normalized Salary (USD):", min_value=10000.0, max_value=1000000.0, value=120000.0, step=1000.0)
                reason_code = st.selectbox("Remediation Reason Code:", ["INTERNAL_EQUITY", "MARKET_PARITY", "DISPARITY_CORRECTION", "PROMOTION_CATCHUP", "RETENTION"])
            with col_f2:
                eff_date = st.date_input("Proposed Effective Date:", value=date(2026, 4, 1))
                created_by = st.text_input("Proposing Actor ID / Email:", "hr.equity.lead@company.org")
                notes = st.text_area("Justification & Clinical Context:", "Adjustment to correct documented market disparity against cohort median.")

            submitted = st.form_submit_button("Submit Draft Proposal")
            if submitted:
                emp = db.query(Employee).filter(Employee.employee_id == prop_emp_id.strip()).first()
                if not emp:
                    st.error(f"Employee '{prop_emp_id}' does not exist in master records.")
                else:
                    latest_sal = db.query(SalaryRecord).filter(
                        SalaryRecord.employee_id == emp.employee_id
                    ).order_by(SalaryRecord.effective_date.desc()).first()
                    curr_sal = latest_sal.normalized_salary if latest_sal else 100000.0

                    try:
                        prop = ProposalManager.create_proposal(
                            session=db,
                            employee_id=emp.employee_id,
                            current_salary=curr_sal,
                            proposed_salary=proposed_salary,
                            reason_code=reason_code,
                            justification_notes=notes,
                            evidence_summary={"manual_submission": True},
                            related_disparity_findings={"status": "MANUAL_REMEDIATION"},
                            proposed_effective_date=eff_date,
                            created_by=created_by
                        )
                        db.commit()
                        st.success(f"Proposal {prop.proposal_id} created successfully in DRAFT status.")
                    except Exception as ex:
                        db.rollback()
                        st.error(f"Failed to create proposal: {ex}")

    st.markdown("---")

    # Proposals Table
    proposals = db.query(AdjustmentProposal).order_by(AdjustmentProposal.created_at.desc()).all()
    if not proposals:
        st.info("No adjustment proposals currently recorded.")
        return

    prop_data = [
        {
            "Proposal ID": p.proposal_id,
            "Employee ID": p.employee_id,
            "Current ($)": f"${p.current_salary:,.0f}",
            "Proposed ($)": f"${p.proposed_salary:,.0f}",
            "Adjustment ($)": f"${p.adjustment_amount:,.0f}",
            "Increase (%)": f"+{p.adjustment_percentage:.1f}%",
            "Reason": p.reason_code,
            "Status": p.approval_status,
            "Proposed Effective": str(p.proposed_effective_date),
            "Created By": p.created_by,
            "Reviewed By": p.reviewed_by or "Pending"
        }
        for p in proposals
    ]

    st.subheader(f"Active Adjustment Proposals Registry ({len(prop_data)} Total)")
    st.dataframe(pd.DataFrame(prop_data), use_container_width=True)
