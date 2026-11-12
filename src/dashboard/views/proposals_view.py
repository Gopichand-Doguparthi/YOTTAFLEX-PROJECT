"""
View 9: Adjustment Proposals Management.
Enables unique proposal initiation, comprehensive filtering, and table management.
"""
import importlib
from datetime import date, datetime
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import AdjustmentProposal, ApprovalEvent, Employee, SalaryRecord, CompensationBand, PerformanceEvidence, Tenure
import src.workflow.audit_logger as audit_logger_mod
import src.workflow.proposal_manager as proposal_manager_mod
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    format_actor_name, fmt_usd, fmt_pct, build_table_column_config,
)


_STANDARD_REASONS = [
    "Internal Equity",
    "Market Parity",
    "Disparity Correction",
    "Promotion Catchup",
    "Retention",
]

_STANDARD_STATUSES = [
    "Draft",
    "Pending Review",
    "Approved",
    "Rejected",
]


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

    emp_choices = _load_employee_choices()
    emp_meta = {e["employee_id"]: e for e in emp_choices}
    label_to_id = {e["label"]: e["employee_id"] for e in emp_choices}

    # Proposal creation form
    with st.expander("Initiate New Compensation Adjustment Proposal", expanded=False):
        selected_emp_label = st.selectbox(
            "Select Employee (search by ID or name):",
            [e["label"] for e in emp_choices],
            index=0,
            key="proposal_emp_selector",
        )
        emp_id = label_to_id.get(selected_emp_label)

        # Load live compensation & equity context for the selected employee
        ctx_curr_sal = 100000.0
        ctx_band_str = "N/A"
        ctx_cohort_med = None
        ctx_rating = None
        ctx_tenure = None
        ctx_status = "N/A"
        rec_salary = 125000.0
        rec_reason_idx = 0
        role_map = get_role_map(db)
        level_map = get_level_map(db)
        loc_map = get_location_map(db)

        if emp_id and emp_id in emp_meta:
            em = emp_meta[emp_id]
            latest_sal = (
                db.query(SalaryRecord)
                .filter(SalaryRecord.employee_id == emp_id)
                .order_by(SalaryRecord.effective_date.desc())
                .first()
            )
            if latest_sal:
                ctx_curr_sal = float(latest_sal.normalized_salary)

            band = (
                db.query(CompensationBand)
                .filter_by(
                    role_id=em["role_id"],
                    level_id=em["level_id"],
                    location_id=em["location_id"],
                    status="ACTIVE",
                )
                .first()
            )
            band_mid_usd = None
            if band:
                curr_norm = get_currency_normalizer(db)
                b_min, b_mid, b_max = get_band_usd_amounts(band, curr_norm)
                band_mid_usd = b_mid
                ctx_band_str = f"{fmt_usd(b_min)} – {fmt_usd(b_mid)} – {fmt_usd(b_max)}"

            # Peer cohort median (2026)
            peer_sals = [
                float(r[0])
                for r in db.query(SalaryRecord.normalized_salary)
                .join(Employee, Employee.employee_id == SalaryRecord.employee_id)
                .filter(
                    Employee.current_role_id == em["role_id"],
                    Employee.current_level_id == em["level_id"],
                    Employee.current_location_id == em["location_id"],
                    SalaryRecord.effective_date >= "2026-01-01",
                )
                .all()
            ]
            if peer_sals:
                peer_sals.sort()
                mid_i = len(peer_sals) // 2
                ctx_cohort_med = peer_sals[mid_i] if len(peer_sals) % 2 == 1 else (peer_sals[mid_i - 1] + peer_sals[mid_i]) / 2.0

            perf = (
                db.query(PerformanceEvidence)
                .filter(PerformanceEvidence.employee_id == emp_id)
                .order_by(PerformanceEvidence.effective_date.desc())
                .first()
            )
            if perf:
                ctx_rating = float(perf.rating_score)

            ten = db.query(Tenure).filter(Tenure.employee_id == emp_id).first()
            if ten:
                ctx_tenure = float(ten.tenure_in_company_years)

            # Determine disparity status & recommended target salary
            target_ref = ctx_cohort_med or band_mid_usd or round(ctx_curr_sal * 1.10, 0)
            dev_pct = ((ctx_curr_sal - ctx_cohort_med) / ctx_cohort_med * 100.0) if ctx_cohort_med else 0.0
            cr_val = (ctx_curr_sal / band_mid_usd) if band_mid_usd else 1.0
            if (dev_pct < -15.0 or cr_val < 0.80) and (ctx_rating or 0) >= 3.5 and (ctx_tenure or 0) >= 1.0:
                ctx_status = "Unexplained Disparity (Flagged)"
                rec_reason_idx = 2  # DISPARITY_CORRECTION
                rec_salary = round(max(target_ref, ctx_curr_sal * 1.10), -2)
            elif cr_val < 0.80:
                ctx_status = "Below Band Target (< 0.80 CR)"
                rec_reason_idx = 1  # MARKET_PARITY
                rec_salary = round(max(band_mid_usd or ctx_curr_sal * 1.10, ctx_curr_sal * 1.08), -2)
            elif cr_val > 1.20:
                ctx_status = "Above Band Ceiling (> 1.20 CR)"
                rec_reason_idx = 1  # MARKET_PARITY
                rec_salary = round(ctx_curr_sal, -2)
            else:
                ctx_status = "In Target Range"
                rec_reason_idx = 0  # INTERNAL_EQUITY
                rec_salary = round(max(target_ref, ctx_curr_sal * 1.06), -2)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Current Salary (USD)", fmt_usd(ctx_curr_sal))
            c2.metric("Peer Cohort Median", fmt_usd(ctx_cohort_med) if ctx_cohort_med else "N/A")
            c3.metric("Performance / Tenure", f"{ctx_rating:.2f}/5" if ctx_rating else "N/A", f"{ctx_tenure:.1f} yrs" if ctx_tenure else None)
            c4.metric("Equity Status", ctx_status.split(" (")[0])
            st.caption(
                f"**Role:** {role_map.get(em['role_id'], em['role_id'])}  |  "
                f"**Level:** {level_map.get(em['level_id'], em['level_id'])}  |  "
                f"**Location:** {loc_map.get(em['location_id'], em['location_id'])}  |  "
                f"**Band (Min–Mid–Max):** {ctx_band_str}"
            )

        reason_codes = ["INTERNAL_EQUITY", "MARKET_PARITY", "DISPARITY_CORRECTION", "PROMOTION_CATCHUP", "RETENTION"]

        with st.form("new_proposal_form", clear_on_submit=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                proposed_salary = st.number_input(
                    "Proposed Normalized Salary (USD):",
                    min_value=1000.0,
                    max_value=5000000.0,
                    value=float(max(1000.0, rec_salary)),
                    step=1000.0,
                    key=f"prop_sal_{emp_id}",
                )
                reason_code = st.selectbox(
                    "Remediation Reason Code:",
                    reason_codes,
                    index=rec_reason_idx,
                    key=f"prop_reason_{emp_id}",
                )
            with col_f2:
                eff_date = st.date_input("Proposed Effective Date:", value=date(2026, 4, 1))
                created_by = st.text_input("Proposing Actor Name / Email:", "HR Equity Lead")
                notes = st.text_area(
                    "Justification & Context:",
                    f"Adjustment for {emp_meta[emp_id]['name']} ({role_map.get(emp_meta[emp_id]['role_id'], '')}) based on {ctx_status.lower()} against peer cohort and band benchmarks.",
                    key=f"prop_notes_{emp_id}",
                )

            submitted = st.form_submit_button("Submit Draft Proposal", type="primary")
            if submitted:
                if not emp_id:
                    st.session_state["proposal_feedback"] = ("error", "Please select a valid employee.")
                else:
                    # Enforce uniqueness: block duplicate identical proposals (or double-clicks)
                    duplicate = (
                        db.query(AdjustmentProposal)
                        .filter(
                            AdjustmentProposal.employee_id == emp_id,
                            AdjustmentProposal.proposed_salary == float(proposed_salary),
                            AdjustmentProposal.reason_code == reason_code,
                            AdjustmentProposal.proposed_effective_date == eff_date,
                        )
                        .first()
                    )
                    if duplicate is not None:
                        st.session_state["proposal_feedback"] = (
                            "warning",
                            f"Duplicate entry prevented: Proposal {duplicate.proposal_id} already exists for "
                            f"{emp_meta[emp_id]['name']} ({emp_id}) with identical salary, reason, and effective date."
                        )
                    else:
                        curr_sal = ctx_curr_sal

                        try:
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
                            st.session_state["proposal_feedback"] = (
                                "success",
                                f"Proposal {prop.proposal_id} created for {emp_meta[emp_id]['name']} ({emp_id}) in DRAFT status."
                            )
                            st.rerun()
                        except Exception as ex:
                            db.rollback()
                            st.session_state["proposal_feedback"] = ("error", f"Failed to create proposal: {ex}")

    # Feedback displayed BELOW the creation form / submit button
    if "proposal_feedback" in st.session_state:
        lvl, msg = st.session_state.pop("proposal_feedback")
        if lvl == "success":
            st.success(msg)
        elif lvl == "warning":
            st.warning(msg)
        else:
            st.error(msg)

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
            "_adj_amt": float(p.adjustment_amount),
        })

    # Comprehensive Filters — always keep ALL standard reasons & statuses
    st.subheader("Filter Proposals")
    fc0, fc1, fc2, fc3, fc4, fc5 = st.columns(6)
    status_opts = ["All"] + sorted(set(_STANDARD_STATUSES) | {r["Status"] for r in all_rows})
    reason_opts = ["All"] + sorted(set(_STANDARD_REASONS) | {r["Reason"] for r in all_rows})
    reviewer_opts = ["All"] + sorted({"Pending"} | {r["Reviewed By"] for r in all_rows})
    date_opts = ["All"] + sorted({r["Proposed Effective"] for r in all_rows})

    with fc0:
        f_emp = st.text_input("Employee Name / ID:", "", placeholder="e.g. EMP-000001")
    with fc1:
        f_status = st.selectbox("Status:", status_opts, index=0)
    with fc2:
        f_reason = st.selectbox("Reason:", reason_opts, index=0)
    with fc3:
        f_dir = st.selectbox("Direction:", ["All", "Increment (+)", "Decrement (-)"], index=0, key="prop_dir")
    with fc4:
        f_date = st.selectbox("Effective Date:", date_opts, index=0)
    with fc5:
        f_reviewer = st.selectbox("Reviewed By:", reviewer_opts, index=0)

    q_emp = f_emp.strip().lower()
    filtered_rows = [
        r for r in all_rows
        if (not q_emp or q_emp in r["Employee ID"].lower() or q_emp in r["Employee Name"].lower() or q_emp in r["Proposal ID"].lower())
        and (f_status == "All" or r["Status"] == f_status)
        and (f_reason == "All" or r["Reason"] == f_reason)
        and (f_dir == "All" or (f_dir == "Increment (+)" and r["_adj_amt"] > 0) or (f_dir == "Decrement (-)" and r["_adj_amt"] < 0))
        and (f_date == "All" or r["Proposed Effective"] == f_date)
        and (f_reviewer == "All" or r["Reviewed By"] == f_reviewer)
    ]

    st.subheader(f"Active Adjustment Proposals Registry ({len(filtered_rows):,} Total)")
    if not filtered_rows:
        st.info("No proposals match the selected filters.")
        return

    disp_df = pd.DataFrame(filtered_rows).drop(columns=["_adj_amt"], errors="ignore")
    st.dataframe(
        disp_df,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(disp_df),
    )
