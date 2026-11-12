"""
View 10: Approval History View.
Tracks formal executive review decisions, justifications, and timestamps.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal, Employee
from src.dashboard.views.helpers import format_actor_name, fmt_usd, fmt_pct, build_table_column_config


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Executive Approval & Decision History")
    st.markdown("Detailed audit of approved and rejected compensation adjustments, executive rationale, and review timestamps.")

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
    ah1, ah2, ah3 = st.columns([2, 1.5, 1.5])
    with ah1:
        ah_search = st.text_input("Search by Proposal ID, Employee ID, or Name:", "", key="ah_search", placeholder="e.g. ADJ-2026 or EMP-")
    with ah2:
        ah_dec = st.selectbox("Filter by Decision:", ["All Decisions", "Approved", "Rejected"], index=0)
    with ah3:
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
    if ah_rev != "All Reviewers":
        df_hist = df_hist[df_hist["Reviewed By"] == ah_rev]

    st.caption(f"Showing {len(df_hist):,} decision record(s)")
    st.dataframe(
        df_hist,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(df_hist),
    )
