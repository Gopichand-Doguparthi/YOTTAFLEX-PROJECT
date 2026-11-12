"""
View 8: Operational Exceptions & Negative Scenarios View.
Exposes the Five Mandatory Edge Cases and Operational Anomalies.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import (
    SalaryRecord, CompensationBand, Employee, AdjustmentProposal,
    ApprovalEvent, GroundTruthRecord
)
from src.engine.currency_normalizer import CurrencyNormalizer
from src.engine.comparable_groups import ComparableGroupEngine
from src.engine.exception_detector import ExceptionDetector
from src.dashboard.views.helpers import (
    get_location_map, PLOTLY_CONFIG, apply_clean_layout, build_table_column_config,
)


_ISSUE_LABELS = {
    "EXPIRED_BAND_COMPARISON": "Expired Band Comparison",
    "FTE_IGNORED_IN_NORMALIZATION": "FTE Ignored in Normalization",
    "MISSING_CURRENCY_CONVERSION": "Missing Currency Conversion",
    "UNAPPROVED_ADJUSTMENT_APPLIED": "Unapproved Adjustment Applied",
    "INCOMPARABLE_ROLE_GROUPING": "Incomparable Role Grouping",
}


def _fmt_val(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    if isinstance(val, (int, float)):
        return f"{val:,.2f}"
    return str(val)


@st.cache_data(ttl=120, show_spinner=False)
def _scan_all_exceptions() -> list:
    """Runs exception detection once and caches results for instant sidebar switching."""
    db = SessionLocal()
    try:
        loc_map = get_location_map(db)
        emp_lookup = {
            e[0]: {
                "name": f"{e[1]} {e[2]}",
                "role_id": e[3],
                "level_id": e[4],
                "location_id": e[5],
                "location_name": loc_map.get(e[5], e[5]),
            }
            for e in db.query(
                Employee.employee_id,
                Employee.first_name,
                Employee.last_name,
                Employee.current_role_id,
                Employee.current_level_id,
                Employee.current_location_id,
            ).all()
        }

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
            emp_info = emp_lookup.get(sal.employee_id, {})

            def _attach_meta(exc_dict):
                exc_dict["record_id"] = sal.salary_id
                exc_dict["employee_id"] = sal.employee_id
                exc_dict["employee_name"] = emp_info.get("name", "—")
                exc_dict["location_name"] = emp_info.get("location_name", "—")
                exc_dict["_role_id"] = emp_info.get("role_id")
                exc_dict["_level_id"] = emp_info.get("level_id")
                exc_dict["_location_id"] = emp_info.get("location_id")
                return exc_dict

            if sal.benchmark_band_id and sal.benchmark_band_id in bands:
                b = bands[sal.benchmark_band_id]
                exc = detector.check_expired_band_comparison(
                    salary_effective_date=sal.effective_date,
                    band_start_date=b.effective_start_date,
                    band_end_date=b.effective_end_date
                )
                if exc:
                    exceptions.append(_attach_meta(exc))

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
                exceptions.append(_attach_meta(exc_fte))

            if sal.currency != "USD":
                if abs(sal.normalized_salary - sal.base_salary) < 1.0 and abs(fx_rate - 1.0) > 0.05:
                    exceptions.append(_attach_meta({
                        "issue_type": "MISSING_CURRENCY_CONVERSION",
                        "severity": "CRITICAL",
                        "description": f"Foreign currency salary ({sal.currency}) was normalized 1:1 without applying an exchange rate.",
                        "detected_value": sal.normalized_salary,
                        "expected_value": round(sal.base_salary * fx_rate, 2),
                        "recommendation": f"Apply the effective-dated {sal.currency}-to-USD exchange rate multiplier."
                    }))

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
                    exceptions.append(_attach_meta(exc_unapp))

        group_records = db.query(GroundTruthRecord).filter_by(issue_type="INCOMPARABLE_ROLE_GROUPING").all()
        for gtr in group_records:
            parts = gtr.record_id.replace("GRP-", "").split("-")
            if len(parts) >= 4:
                role_a = f"{parts[0]}-{parts[1]}"
                role_b = f"{parts[2]}-{parts[3]}"
                exc_grp = detector.check_incomparable_roles_grouped(role_a, role_b)
                if exc_grp:
                    exc_grp["record_id"] = gtr.record_id
                    exc_grp["employee_id"] = "Group Mapping"
                    exc_grp["employee_name"] = "—"
                    exc_grp["location_name"] = "Global"
                    exc_grp["_role_id"] = None
                    exc_grp["_level_id"] = None
                    exc_grp["_location_id"] = None
                    exceptions.append(exc_grp)

        return exceptions
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Operational Exceptions & Mandatory Edge Case Diagnostics")
    st.markdown("Dedicated isolation of system exceptions, boundary failures, and compliance anomalies across the 5 mandatory edge cases.")

    all_exceptions = _scan_all_exceptions()
    exceptions = [
        e for e in all_exceptions
        if (selected_role == "All" or e.get("_role_id") in (None, selected_role))
        and (selected_level == "All" or e.get("_level_id") in (None, selected_level))
        and (selected_location == "All" or e.get("_location_id") in (None, selected_location))
    ]

    df_exc = pd.DataFrame(exceptions)

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

    if not df_exc.empty:
        df_exc["Issue Label"] = df_exc["issue_type"].map(lambda x: _ISSUE_LABELS.get(x, x))

        st.subheader("Exception Incidents by Issue Type")
        issue_summary = df_exc["Issue Label"].value_counts().reset_index()
        issue_summary.columns = ["Issue Type", "Count"]
        fig_bar = px.bar(
            issue_summary,
            x="Issue Type",
            y="Count",
            color="Issue Type",
            text="Count",
            title="Exception Incidents by Issue Type",
        )
        fig_bar.update_traces(textposition="outside", cliponaxis=False)
        apply_clean_layout(fig_bar, legend_bottom=True, height=530, xaxis_tickangle=-15, extra_bottom_margin=20)
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)

        st.subheader("Exception Incidents by Severity Level")
        sev_summary = df_exc["severity"].value_counts().reset_index()
        sev_summary.columns = ["Severity", "Count"]
        fig_sev = px.pie(
            sev_summary,
            names="Severity",
            values="Count",
            hole=0.42,
            title="Exception Incidents by Severity Level",
            color="Severity",
            color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308"}
        )
        fig_sev.update_traces(marker=dict(line=dict(color="#0f172a", width=2)))
        apply_clean_layout(fig_sev, legend_bottom=True, height=420, legend_position="bottom")
        st.plotly_chart(fig_sev, use_container_width=True, config=PLOTLY_CONFIG)

        st.subheader("Detailed Exception Diagnostic Logs")
        df_display = pd.DataFrame({
            "Employee ID": df_exc["employee_id"],
            "Employee Name": df_exc["employee_name"],
            "Record ID": df_exc["record_id"],
            "Location": df_exc["location_name"],
            "Issue Type": df_exc["Issue Label"],
            "Severity": df_exc["severity"],
            "Detected Value": df_exc["detected_value"].map(_fmt_val) if "detected_value" in df_exc else "—",
            "Expected Value": df_exc["expected_value"].map(_fmt_val) if "expected_value" in df_exc else "—",
            "Description": df_exc["description"],
            "Recommendation": df_exc["recommendation"],
        }).sort_values(["Employee ID", "Record ID"])

        ef1, ef2, ef3 = st.columns([2, 1.5, 1.5])
        with ef1:
            exc_search = st.text_input("Search by Employee ID, Name, or Record ID:", "", key="exc_search", placeholder="e.g. EMP-000100 or SAL-")
        with ef2:
            exc_issue_opt = st.selectbox("Filter by Issue Type:", ["All Issue Types"] + list(_ISSUE_LABELS.values()), index=0)
        with ef3:
            exc_sev_opt = st.selectbox("Filter by Severity:", ["All Severities", "CRITICAL", "HIGH", "MEDIUM"], index=0)

        if exc_search.strip():
            q = exc_search.strip().lower()
            df_display = df_display[
                df_display["Employee ID"].str.lower().str.contains(q, na=False)
                | df_display["Employee Name"].str.lower().str.contains(q, na=False)
                | df_display["Record ID"].str.lower().str.contains(q, na=False)
            ]
        if exc_issue_opt != "All Issue Types":
            df_display = df_display[df_display["Issue Type"] == exc_issue_opt]
        if exc_sev_opt != "All Severities":
            df_display = df_display[df_display["Severity"] == exc_sev_opt]

        st.caption(f"Showing {len(df_display):,} exception record(s)")
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config=build_table_column_config(df_display),
        )
    else:
        st.success("No exceptions detected across the selected scope.")
