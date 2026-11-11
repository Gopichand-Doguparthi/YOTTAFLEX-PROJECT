"""
View 8: Operational Exceptions & Negative Scenarios View.
Exposes the Five Mandatory Edge Cases and Operational Anomalies.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models import (
    SalaryRecord, CompensationBand, Employee, AdjustmentProposal,
    ApprovalEvent, GroundTruthRecord
)
from src.engine.currency_normalizer import CurrencyNormalizer
from src.engine.comparable_groups import ComparableGroupEngine
from src.engine.exception_detector import ExceptionDetector


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Operational Exceptions & Mandatory Edge Case Diagnostics")
    st.markdown("Dedicated isolation of system exceptions, boundary failures, and compliance anomalies across the 5 mandatory edge cases.")

    curr_norm = CurrencyNormalizer()
    curr_norm.load_from_db(db)

    group_engine = ComparableGroupEngine()
    group_engine.load_rationales_from_db(db)

    detector = ExceptionDetector(curr_norm, group_engine)

    salaries = db.query(SalaryRecord).all()
    bands = {b.band_id: b for b in db.query(CompensationBand).all()}
    proposals = {p.employee_id: p for p in db.query(AdjustmentProposal).all()}
    approved_audit_events = {
        e.entity_id for e in db.query(ApprovalEvent).filter(
            ApprovalEvent.event_type.in_(["PROPOSAL_APPROVED", "SALARY_UPDATED"])
        ).all()
    }

    exceptions = []

    for sal in salaries:
        # Check 1: Expired band
        if sal.benchmark_band_id and sal.benchmark_band_id in bands:
            b = bands[sal.benchmark_band_id]
            exc = detector.check_expired_band_comparison(
                salary_effective_date=sal.effective_date,
                band_start_date=b.effective_start_date,
                band_end_date=b.effective_end_date
            )
            if exc:
                exc["record_id"] = sal.salary_id
                exc["employee_id"] = sal.employee_id
                exceptions.append(exc)

        # Check 2: FTE ignored
        fx_rate = 1.0
        try:
            fx_rate = curr_norm.get_rate(sal.currency, "USD", sal.effective_date)
        except Exception:
            pass

        exc_fte = detector.check_fte_ignored(
            recorded_normalized_salary=sal.normalized_salary,
            base_salary=sal.base_salary,
            fte=sal.fte,
            pay_frequency=sal.pay_frequency,
            fx_rate=fx_rate
        )
        if exc_fte:
            exc_fte["record_id"] = sal.salary_id
            exc_fte["employee_id"] = sal.employee_id
            exceptions.append(exc_fte)

        # Check 3: Currency conversion missing
        if sal.currency != "USD":
            if abs(sal.normalized_salary - sal.base_salary) < 1.0 and abs(fx_rate - 1.0) > 0.05:
                exceptions.append({
                    "issue_type": "MISSING_CURRENCY_CONVERSION",
                    "severity": "CRITICAL",
                    "record_id": sal.salary_id,
                    "employee_id": sal.employee_id,
                    "description": f"Foreign currency salary ({sal.currency}) normalized 1:1 without exchange rate.",
                    "detected_value": sal.normalized_salary,
                    "expected_value": round(sal.base_salary * fx_rate, 2),
                    "recommendation": f"Apply effective-dated {sal.currency}->USD FX multiplier."
                })

        # Check 4: Unapproved adjustment applied
        if sal.change_reason in ["EQUITY_CORRECTION", "MARKET_ADJUSTMENT"]:
            prop = proposals.get(sal.employee_id)
            prop_status = prop.approval_status if prop else None
            has_audit = (sal.salary_id in approved_audit_events) or (prop and prop.proposal_id in approved_audit_events)
            exc_unapp = detector.check_unapproved_adjustment_applied(
                salary_change_reason=sal.change_reason,
                proposal_status=prop_status,
                has_approved_audit_event=has_audit
            )
            if exc_unapp:
                exc_unapp["record_id"] = sal.salary_id
                exc_unapp["employee_id"] = sal.employee_id
                exceptions.append(exc_unapp)

    # Check 5: Incomparable roles grouped
    group_records = db.query(GroundTruthRecord).filter_by(issue_type="INCOMPARABLE_ROLE_GROUPING").all()
    for gtr in group_records:
        parts = gtr.record_id.replace("GRP-", "").split("-")
        if len(parts) >= 4:
            role_a = f"{parts[0]}-{parts[1]}"
            role_b = f"{parts[2]}-{parts[3]}"
            exc_grp = detector.check_incomparable_roles_grouped(role_a, role_b)
            if exc_grp:
                exc_grp["record_id"] = gtr.record_id
                exc_grp["employee_id"] = "N/A (Group Mapping)"
                exceptions.append(exc_grp)

    df_exc = pd.DataFrame(exceptions)

    # Scorecards for the 5 mandatory edge cases
    counts = {
        "EXPIRED_BAND_COMPARISON": len(df_exc[df_exc["issue_type"] == "EXPIRED_BAND_COMPARISON"]) if not df_exc.empty else 0,
        "FTE_IGNORED_IN_NORMALIZATION": len(df_exc[df_exc["issue_type"] == "FTE_IGNORED_IN_NORMALIZATION"]) if not df_exc.empty else 0,
        "MISSING_CURRENCY_CONVERSION": len(df_exc[df_exc["issue_type"] == "MISSING_CURRENCY_CONVERSION"]) if not df_exc.empty else 0,
        "UNAPPROVED_ADJUSTMENT_APPLIED": len(df_exc[df_exc["issue_type"] == "UNAPPROVED_ADJUSTMENT_APPLIED"]) if not df_exc.empty else 0,
        "INCOMPARABLE_ROLE_GROUPING": len(df_exc[df_exc["issue_type"] == "INCOMPARABLE_ROLE_GROUPING"]) if not df_exc.empty else 0,
    }

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("1. Expired Bands", counts["EXPIRED_BAND_COMPARISON"])
    col2.metric("2. FTE Ignored", counts["FTE_IGNORED_IN_NORMALIZATION"])
    col3.metric("3. Missing FX", counts["MISSING_CURRENCY_CONVERSION"])
    col4.metric("4. Unapproved Adj.", counts["UNAPPROVED_ADJUSTMENT_APPLIED"])
    col5.metric("5. Incomp. Roles", counts["INCOMPARABLE_ROLE_GROUPING"])

    st.markdown("---")

    # Issue breakdown chart
    if not df_exc.empty:
        col_bar, col_sev = st.columns(2)
        with col_bar:
            issue_summary = df_exc["issue_type"].value_counts().reset_index()
            issue_summary.columns = ["Issue Type", "Count"]
            fig_bar = px.bar(
                issue_summary,
                x="Issue Type",
                y="Count",
                color="Issue Type",
                title="Exception Incidents by Issue Type"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_sev:
            sev_summary = df_exc["severity"].value_counts().reset_index()
            sev_summary.columns = ["Severity", "Count"]
            fig_sev = px.pie(
                sev_summary,
                names="Severity",
                values="Count",
                title="Exception Incidents by Severity Level",
                color="Severity",
                color_discrete_map={"CRITICAL": "#e74c3c", "HIGH": "#e67e22", "MEDIUM": "#f1c40f"}
            )
            st.plotly_chart(fig_sev, use_container_width=True)

        st.subheader("Detailed Exception Diagnostic Logs")
        st.dataframe(df_exc, use_container_width=True)
    else:
        st.success("No exceptions detected across the database.")
