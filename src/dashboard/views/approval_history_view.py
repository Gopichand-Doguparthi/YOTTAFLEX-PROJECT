"""
View 10: Approval History View.
Tracks formal executive review decisions, justifications, and timestamps.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal, Employee
from src.workflow.proposal_manager import (
    ProposalManager, InvalidLifecycleTransitionException, UnauthorizedApprovalException
)
from src.dashboard.views.helpers import format_actor_name, fmt_usd, fmt_pct, build_table_column_config


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Approval & Decision History")
    st.markdown("Submit draft proposals, render authorized approval/rejection decisions, and audit historical outcomes.")

    emp_lookup = {
        e[0]: (f"{e[1]} {e[2]}", e[3], e[4], e[5])
        for e in db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
        ).all()
    }

    proposals = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.approval_status.in_(["APPROVED", "REJECTED"])
    ).order_by(AdjustmentProposal.reviewed_at.desc()).all()

    # Interactive Workflow Actions (Submit DRAFT / Review PENDING_REVIEW)
    draft_props = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.approval_status == "DRAFT"
    ).order_by(AdjustmentProposal.created_at.desc()).all()
    pending_props = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.approval_status == "PENDING_REVIEW"
    ).order_by(AdjustmentProposal.created_at.desc()).all()

    act_col1, act_col2 = st.columns(2)
    with act_col1:
        with st.expander(f"Submit Draft Proposals for Review ({len(draft_props)})", expanded=False):
            if not draft_props:
                st.info("No DRAFT proposals awaiting submission.")
            else:
                draft_map = {
                    f"{p.proposal_id} | {p.employee_id} ({fmt_usd(p.adjustment_amount)})": p
                    for p in draft_props
                }
                sel_draft_lbl = st.selectbox("Select Draft Proposal:", list(draft_map.keys()), key="ah_draft_sel")
                sub_actor = st.text_input("Submitted By:", value="hr.partner@company.org", key="ah_sub_actor")
                sub_notes = st.text_input("Submission Notes:", value="Submitted for compensation committee review.", key="ah_sub_notes")
                if st.button("Submit for Review", key="ah_sub_btn", type="primary"):
                    try:
                        ProposalManager.submit_for_review(
                            session=db,
                            proposal_id=draft_map[sel_draft_lbl].proposal_id,
                            submitted_by=sub_actor,
                            notes=sub_notes,
                        )
                        db.commit()
                        st.cache_data.clear()
                        st.success(f"Proposal {draft_map[sel_draft_lbl].proposal_id} moved to PENDING_REVIEW.")
                        st.rerun()
                    except Exception as exc:
                        db.rollback()
                        st.error(f"Submission failed: {exc}")

    with act_col2:
        with st.expander(f"Pending Approval Queue ({len(pending_props)})", expanded=len(pending_props) > 0):
            if not pending_props:
                st.info("No PENDING_REVIEW proposals in queue.")
            else:
                pend_map = {
                    f"{p.proposal_id} | {p.employee_id} ({fmt_usd(p.current_salary)} -> {fmt_usd(p.proposed_salary)})": p
                    for p in pending_props
                }
                sel_pend_lbl = st.selectbox("Select Pending Proposal:", list(pend_map.keys()), key="ah_pend_sel")
                sel_pend = pend_map[sel_pend_lbl]
                st.caption(f"Created by: {sel_pend.created_by} | Reason: {sel_pend.reason_code}")
                rev_actor = st.text_input("Reviewer Email:", value="manager.lead@company.org", key="ah_rev_actor")
                rev_role = st.selectbox("Reviewer Role:", ["MANAGER", "HR_PARTNER", "SYSTEM_ADMIN", "COMP_COMMITTEE", "EMPLOYEE"], index=0, key="ah_rev_role")
                rev_notes = st.text_input("Decision Notes:", value="Verified against peer cohort & performance evidence.", key="ah_rev_notes")
                b1, b2 = st.columns(2)
                if b1.button("Approve Adjustment", key="ah_app_btn", type="primary"):
                    try:
                        ProposalManager.approve_proposal(
                            session=db,
                            proposal_id=sel_pend.proposal_id,
                            reviewed_by=rev_actor,
                            actor_role=rev_role,
                            review_notes=rev_notes,
                            apply_salary_update=True,
                        )
                        db.commit()
                        st.cache_data.clear()
                        st.success(f"Approved {sel_pend.proposal_id} and recorded audit event.")
                        st.rerun()
                    except (UnauthorizedApprovalException, InvalidLifecycleTransitionException, Exception) as exc:
                        db.rollback()
                        st.error(f"Approval blocked: {exc}")
                if b2.button("Reject Adjustment", key="ah_rej_btn"):
                    try:
                        ProposalManager.reject_proposal(
                            session=db,
                            proposal_id=sel_pend.proposal_id,
                            reviewed_by=rev_actor,
                            actor_role=rev_role,
                            review_notes=rev_notes,
                        )
                        db.commit()
                        st.cache_data.clear()
                        st.warning(f"Rejected {sel_pend.proposal_id} and recorded audit event.")
                        st.rerun()
                    except (UnauthorizedApprovalException, InvalidLifecycleTransitionException, Exception) as exc:
                        db.rollback()
                        st.error(f"Rejection blocked: {exc}")

    st.markdown("---")

    filtered_props = []
    for p in proposals:
        info = emp_lookup.get(p.employee_id)
        if info:
            _, r_id, l_id, loc_id = info
            if selected_role != "All" and r_id != selected_role:
                continue
            if selected_level != "All" and l_id != selected_level:
                continue
            if selected_location != "All" and loc_id != selected_location:
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
        info = emp_lookup.get(p.employee_id)
        emp_name = info[0] if info else "Unknown"
        hist_data.append({
            "Proposal ID": p.proposal_id,
            "Employee ID": p.employee_id,
            "Employee Name": emp_name,
            "Current (USD)": fmt_usd(p.current_salary),
            "Proposed (USD)": fmt_usd(p.proposed_salary),
            "Adjustment (USD)": fmt_usd(p.adjustment_amount),
            "Increase (%)": fmt_pct(p.adjustment_percentage, 1, signed=True),
            "Decision": p.approval_status.title(),
            "Reviewed By": format_actor_name(p.reviewed_by, fallback="Pending"),
            "Decision Date": str(p.reviewed_at)[:19] if p.reviewed_at else "N/A",
            "Reviewer Notes": p.review_notes or ""
        })

    st.subheader("Historical Decision Ledger")
    st.caption("Note: All 250 seeded proposals in the benchmark dataset are positive equity increments. Any decrement proposals created via the Proposals form (`Proposed < Current`) also appear here.")
    ah1, ah2, ah3, ah4 = st.columns([2, 1.3, 1.3, 1.4])
    with ah1:
        ah_search = st.text_input("Search by Proposal ID, Employee ID, or Name:", "", key="ah_search", placeholder="e.g. ADJ-2026 or EMP-")
    with ah2:
        ah_dec = st.selectbox("Filter by Decision:", ["All Decisions", "Approved", "Rejected"], index=0)
    with ah3:
        ah_dir = st.selectbox("Adjustment Direction:", ["All Directions", "Increment (+)", "Decrement (-)"], index=0, key="ah_dir")
    with ah4:
        reviewer_opts = ["All Reviewers"] + sorted({h["Reviewed By"] for h in hist_data})
        ah_rev = st.selectbox("Filter by Reviewed By:", reviewer_opts, index=0)

    df_hist = pd.DataFrame(hist_data)
    if ah_search.strip():
        q = ah_search.strip().lower()
        df_hist = df_hist[
            df_hist["Proposal ID"].str.lower().str.contains(q, na=False)
            | df_hist["Employee ID"].str.lower().str.contains(q, na=False)
            | df_hist["Employee Name"].str.lower().str.contains(q, na=False)
        ]
    if ah_dec != "All Decisions":
        df_hist = df_hist[df_hist["Decision"] == ah_dec]
    if ah_dir == "Increment (+)":
        df_hist = df_hist[~df_hist["Adjustment (USD)"].astype(str).str.startswith("-") & (df_hist["Adjustment (USD)"].astype(str) != "$0")]
    elif ah_dir == "Decrement (-)":
        df_hist = df_hist[df_hist["Adjustment (USD)"].astype(str).str.startswith("-")]
    if ah_rev != "All Reviewers":
        df_hist = df_hist[df_hist["Reviewed By"] == ah_rev]

    st.caption(f"Showing {len(df_hist):,} decision record(s)")
    st.dataframe(
        df_hist,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(df_hist),
    )
