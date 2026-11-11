"""
View 10: Approval History View.
Tracks formal executive review decisions, justifications, and timestamps.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Approval & Decision History")
    st.markdown("Detailed audit of approved and rejected compensation adjustments, executive rationale, and review timestamps.")

    proposals = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.approval_status.in_(["APPROVED", "REJECTED"])
    ).order_by(AdjustmentProposal.reviewed_at.desc()).all()

    if not proposals:
        st.info("No reviewed proposals found.")
        return

    approved_count = sum(1 for p in proposals if p.approval_status == "APPROVED")
    rejected_count = sum(1 for p in proposals if p.approval_status == "REJECTED")
    approval_rate = (approved_count / len(proposals)) * 100.0 if proposals else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Decisions Rendered", len(proposals))
    col2.metric("Approved Adjustments", approved_count, f"{approval_rate:.1f}% approval rate")
    col3.metric("Rejected Adjustments", rejected_count, delta=f"{rejected_count} rejected", delta_color="inverse")

    st.markdown("---")

    hist_data = [
        {
            "Proposal ID": p.proposal_id,
            "Employee ID": p.employee_id,
            "Current ($)": p.current_salary,
            "Proposed ($)": p.proposed_salary,
            "Adjustment ($)": p.adjustment_amount,
            "Increase (%)": p.adjustment_percentage,
            "Decision": p.approval_status,
            "Reviewed By": p.reviewed_by,
            "Decision Date": str(p.reviewed_at)[:19] if p.reviewed_at else "N/A",
            "Reviewer Notes": p.review_notes
        }
        for p in proposals
    ]
    df_hist = pd.DataFrame(hist_data)

    st.subheader("Historical Decision Ledger")
    st.dataframe(df_hist, use_container_width=True)
