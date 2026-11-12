"""
View 10: Approval History View.
Tracks formal executive review decisions, justifications, and timestamps.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal, Employee
from src.dashboard.views.helpers import format_actor_name


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Approval & Decision History")
    st.markdown("Detailed audit of approved and rejected compensation adjustments, executive rationale, and review timestamps.")

    emp_lookup = {e.employee_id: e for e in db.query(Employee).all()}

    proposals = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.approval_status.in_(["APPROVED", "REJECTED"])
    ).order_by(AdjustmentProposal.reviewed_at.desc()).all()

    filtered_props = []
    for p in proposals:
        emp = emp_lookup.get(p.employee_id)
        if emp:
            if selected_role != "All" and emp.current_role_id != selected_role:
                continue
            if selected_level != "All" and emp.current_level_id != selected_level:
                continue
            if selected_location != "All" and emp.current_location_id != selected_location:
                continue
        filtered_props.append(p)

    if not filtered_props:
        st.info("No reviewed proposals found.")
        return

    approved_count = sum(1 for p in filtered_props if p.approval_status == "APPROVED")
    rejected_count = sum(1 for p in filtered_props if p.approval_status == "REJECTED")
    approval_rate = (approved_count / len(filtered_props)) * 100.0 if filtered_props else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Decisions Rendered", f"{len(filtered_props):,}")
    col2.metric("Approved Adjustments", f"{approved_count:,}", f"{approval_rate:.1f}% approval rate")
    col3.metric("Rejected Adjustments", f"{rejected_count:,}", delta=f"{rejected_count} rejected", delta_color="inverse")

    st.markdown("---")

    hist_data = []
    for p in filtered_props:
        emp = emp_lookup.get(p.employee_id)
        emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
        hist_data.append({
            "Proposal ID": p.proposal_id,
            "Employee ID": p.employee_id,
            "Employee Name": emp_name,
            "Current ($)": float(p.current_salary),
            "Proposed ($)": float(p.proposed_salary),
            "Adjustment ($)": float(p.adjustment_amount),
            "Increase (%)": float(p.adjustment_percentage),
            "Decision": p.approval_status.title(),
            "Reviewed By": format_actor_name(p.reviewed_by, fallback="Pending"),
            "Decision Date": str(p.reviewed_at)[:19] if p.reviewed_at else "N/A",
            "Reviewer Notes": p.review_notes or ""
        })
    df_hist = pd.DataFrame(hist_data)

    st.subheader("Historical Decision Ledger")
    st.dataframe(
        df_hist,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Current ($)": st.column_config.NumberColumn("Current ($)", format="$%,.0f"),
            "Proposed ($)": st.column_config.NumberColumn("Proposed ($)", format="$%,.0f"),
            "Adjustment ($)": st.column_config.NumberColumn("Adjustment ($)", format="$%,.0f"),
            "Increase (%)": st.column_config.NumberColumn("Increase (%)", format="%.1f%%"),
        },
    )
