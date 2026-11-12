"""
View 9: Adjustment Proposals Management.
Enables review, filtering, and initiation of compensation remediation proposals.
"""
import importlib
from datetime import date, datetime
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import AdjustmentProposal, ApprovalEvent, Employee, SalaryRecord
import src.workflow.audit_logger as audit_logger_mod
import src.workflow.proposal_manager as proposal_manager_mod
from src.dashboard.views.helpers import (
    get_role_map, format_actor_name, fmt_usd, fmt_pct,
)


def _next_proposal_id(db: Session, year: int) -> str:
    """Computes the next unused ADJ-YYYY-XXXXXX directly from the database."""
    prefix = f"ADJ-{year}-"
    existing = db.query(AdjustmentProposal.proposal_id).filter(
        AdjustmentProposal.proposal_id.like(f"{prefix}%")
    ).all()
    max_seq = 0
    for (pid,) in existing:
        suffix = pid[len(prefix):]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    return f"{prefix}{max_seq + 1:06d}"


def _sync_audit_counter(db: Session, AuditLogger):
    """Syncs AuditLogger._counter with today's max EVT-YYYYMMDD-XXXXXX in DB."""
    prefix = f"EVT-{datetime.utcnow().strftime('%Y%m%d')}-"
    existing = db.query(ApprovalEvent.event_id).filter(
        ApprovalEvent.event_id.like(f"{prefix}%")
    ).all()
    max_seq = 0
    for (eid,) in existing:
        suffix = eid[len(prefix):]
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    if AuditLogger._counter < max_seq:
        AuditLogger._counter = max_seq


@st.cache_data(ttl=120, show_spinner=False)
def _load_employee_choices() -> list:
    """Loads lightweight employee options for fast proposal form dropdowns."""
    db = SessionLocal()
    try:
        role_map = get_role_map(db)
        rows = db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
        ).order_by(Employee.employee_id.asc()).all()
        return [
            {
                "employee_id": r[0],
                "name": f"{r[1]} {r[2]}",
                "label": f"{r[0]} — {r[1]} {r[2]} ({role_map.get(r[3], r[3])})",
                "role_id": r[3],
                "level_id": r[4],
                "location_id": r[5],
            }
            for r in rows
        ]
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Compensation Adjustment Proposals")
    st.markdown("Manages equity adjustment proposals, approval workflows, and remediation actions.")

    if "proposal_created_msg" in st.session_state:
        st.success(st.session_state.pop("proposal_created_msg"))

    emp_choices = _load_employee_choices()
    emp_meta = {e["employee_id"]: e for e in emp_choices}
    label_to_id = {e["label"]: e["employee_id"] for e in emp_choices}

    # Proposal creation form
    with st.expander("Initiate New Compensation Adjustment Proposal", expanded=False):
        with st.form("new_proposal_form", clear_on_submit=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                selected_emp_label = st.selectbox(
                    "Select Employee (search by ID or name):",
                    [e["label"] for e in emp_choices],
                    index=0,
                )
                proposed_salary = st.number_input(
                    "Proposed Normalized Salary (USD):",
                    min_value=1000.0,
                    max_value=5000000.0,
                    value=125000.0,
                    step=1000.0,
                )
                reason_code = st.selectbox(
                    "Remediation Reason Code:",
                    ["INTERNAL_EQUITY", "MARKET_PARITY", "DISPARITY_CORRECTION", "PROMOTION_CATCHUP", "RETENTION"],
                )
            with col_f2:
                eff_date = st.date_input("Proposed Effective Date:", value=date(2026, 4, 1))
                created_by = st.text_input("Proposing Actor Name / Email:", "HR Equity Lead")
                notes = st.text_area(
                    "Justification & Context:",
                    "Adjustment to correct documented market disparity against cohort median.",
                )

            submitted = st.form_submit_button("Submit Draft Proposal", type="primary")
            if submitted:
                emp_id = label_to_id.get(selected_emp_label)
                if not emp_id:
                    st.error("Please select a valid employee.")
                else:
                    latest_sal = (
                        db.query(SalaryRecord)
                        .filter(SalaryRecord.employee_id == emp_id)
                        .order_by(SalaryRecord.effective_date.desc())
                        .first()
                    )
                    curr_sal = float(latest_sal.normalized_salary) if latest_sal else 100000.0

                    try:
                        # Reload workflow modules in case Streamlit kept older in-memory module state
                        importlib.reload(audit_logger_mod)
                        importlib.reload(proposal_manager_mod)
                        ProposalManager = proposal_manager_mod.ProposalManager
                        AuditLogger = audit_logger_mod.AuditLogger

                        next_pid = _next_proposal_id(db, eff_date.year)
                        _sync_audit_counter(db, AuditLogger)

                        prop = ProposalManager.create_proposal(
                            session=db,
                            employee_id=emp_id,
                            current_salary=curr_sal,
                            proposed_salary=float(proposed_salary),
                            reason_code=reason_code,
                            justification_notes=notes.strip() or "Compensation equity adjustment.",
                            evidence_summary={"manual_submission": True},
                            related_disparity_findings={"status": "MANUAL_REMEDIATION"},
                            proposed_effective_date=eff_date,
                            created_by=created_by.strip() or "HR Equity Lead",
                            custom_id=next_pid,
                        )
                        db.commit()
                        st.cache_data.clear()
                        st.session_state["proposal_created_msg"] = (
                            f"Proposal {prop.proposal_id} created for {emp_meta[emp_id]['name']} ({emp_id}) in DRAFT status."
                        )
                        st.rerun()
                    except Exception as ex:
                        db.rollback()
                        st.error(f"Failed to create proposal: {ex}")

    st.markdown("---")

    proposals = db.query(AdjustmentProposal).order_by(AdjustmentProposal.created_at.desc()).all()
    if not proposals:
        st.info("No adjustment proposals currently recorded.")
        return

    all_rows = []
    for p in proposals:
        meta = emp_meta.get(p.employee_id)
        if meta:
            if selected_role != "All" and meta["role_id"] != selected_role:
                continue
            if selected_level != "All" and meta["level_id"] != selected_level:
                continue
            if selected_location != "All" and meta["location_id"] != selected_location:
                continue
        emp_name = meta["name"] if meta else "Unknown"
        status_label = p.approval_status.replace("_", " ").title()
        reason_label = p.reason_code.replace("_", " ").title()
        reviewer_label = format_actor_name(p.reviewed_by, fallback="Pending")

        all_rows.append({
            "Proposal ID": p.proposal_id,
            "Employee ID": p.employee_id,
            "Employee Name": emp_name,
            "Current (USD)": fmt_usd(p.current_salary),
            "Proposed (USD)": fmt_usd(p.proposed_salary),
            "Adjustment (USD)": fmt_usd(p.adjustment_amount),
            "Change (%)": fmt_pct(p.adjustment_percentage, 1, signed=True),
            "Reason": reason_label,
            "Status": status_label,
            "Proposed Effective": str(p.proposed_effective_date),
            "Created By": format_actor_name(p.created_by, fallback="HR Partner"),
            "Reviewed By": reviewer_label,
            "_eff_date": p.proposed_effective_date,
        })

    # Registry Filters: Status, Reason, Date, Reviewed By
    st.subheader("Filter Proposals")
    fc1, fc2, fc3, fc4 = st.columns(4)
    status_opts = ["All"] + sorted({r["Status"] for r in all_rows})
    reason_opts = ["All"] + sorted({r["Reason"] for r in all_rows})
    reviewer_opts = ["All"] + sorted({r["Reviewed By"] for r in all_rows})
    date_opts = ["All"] + sorted({r["Proposed Effective"] for r in all_rows})

    with fc1:
        f_status = st.selectbox("Status:", status_opts, index=0)
    with fc2:
        f_reason = st.selectbox("Reason:", reason_opts, index=0)
    with fc3:
        f_date = st.selectbox("Proposed Effective Date:", date_opts, index=0)
    with fc4:
        f_reviewer = st.selectbox("Reviewed By:", reviewer_opts, index=0)

    filtered_rows = [
        r for r in all_rows
        if (f_status == "All" or r["Status"] == f_status)
        and (f_reason == "All" or r["Reason"] == f_reason)
        and (f_date == "All" or r["Proposed Effective"] == f_date)
        and (f_reviewer == "All" or r["Reviewed By"] == f_reviewer)
    ]

    st.subheader(f"Active Adjustment Proposals Registry ({len(filtered_rows):,} Total)")
    if not filtered_rows:
        st.info("No proposals match the selected filters.")
        return

    disp_df = pd.DataFrame(filtered_rows).drop(columns=["_eff_date"])
    st.dataframe(disp_df, use_container_width=True, hide_index=True)
