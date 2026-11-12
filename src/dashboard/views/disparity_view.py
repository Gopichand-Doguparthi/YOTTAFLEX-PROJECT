"""
View 6: Disparity Detection and Evidence View.
Evaluates multi-factor compensation disparities against peer cohorts and performance evidence.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.database.models import Employee, SalaryRecord, CompensationBand, PerformanceEvidence, Tenure
from src.engine.disparity_detector import DisparityDetector
from src.dashboard.views.helpers import (
    get_role_map, get_level_map, get_location_map,
    get_currency_normalizer, get_band_usd_amounts,
    fmt_usd, fmt_pct, PLOTLY_CONFIG, apply_clean_layout, build_table_column_config,
)


_STATUS_LABELS = {
    "UNEXPLAINED_DISPARITY": "Unexplained Disparity",
    "MANUAL_REVIEW_REQUIRED": "Manual Review Required",
    "EXPLAINED_VARIATION": "Explained Variation",
    "INSUFFICIENT_EVIDENCE": "Insufficient Evidence",
}

_STATUS_COLORS = {
    "Unexplained Disparity": "#ef4444",
    "Manual Review Required": "#f59e0b",
    "Explained Variation": "#22c55e",
    "Insufficient Evidence": "#38bdf8",
}


@st.cache_data(ttl=120, show_spinner=False)
def _load_disparity_findings() -> pd.DataFrame:
    """Computes and caches multi-factor disparity findings across all employees."""
    db = SessionLocal()
    try:
        role_map = get_role_map(db)
        level_map = get_level_map(db)
        loc_map = get_location_map(db)
        curr_norm = get_currency_normalizer(db)
        detector = DisparityDetector()

        employees = db.query(
            Employee.employee_id,
            Employee.first_name,
            Employee.last_name,
            Employee.department,
            Employee.current_role_id,
            Employee.current_level_id,
            Employee.current_location_id,
        ).all()

        latest_sals = {
            r[0]: float(r[1])
            for r in db.query(SalaryRecord.employee_id, SalaryRecord.normalized_salary)
            .filter(SalaryRecord.effective_date >= "2026-01-01")
            .all()
        }

        band_lookup = {
            (b.role_id, b.level_id, b.location_id): b
            for b in db.query(CompensationBand).filter(CompensationBand.status == "ACTIVE").all()
        }

        cohort_salaries = {}
        for eid, _, _, _, r_id, l_id, loc_id in employees:
            sal = latest_sals.get(eid)
            if sal is not None:
                key = f"{r_id}::{l_id}::{loc_id}"
                cohort_salaries.setdefault(key, []).append(sal)

        cohort_medians = {k: float(np.median(v)) for k, v in cohort_salaries.items()}
        cohort_sizes = {k: len(v) for k, v in cohort_salaries.items()}

        latest_perf = {}
        for eid, rating, eff_date in db.query(
            PerformanceEvidence.employee_id,
            PerformanceEvidence.rating_score,
            PerformanceEvidence.effective_date,
        ).all():
            if eid not in latest_perf or eff_date > latest_perf[eid][1]:
                latest_perf[eid] = (float(rating), eff_date)

        tenures = {
            t[0]: (float(t[1]), float(t[2]))
            for t in db.query(
                Tenure.employee_id,
                Tenure.tenure_in_company_years,
                Tenure.tenure_in_role_years,
            ).all()
        }

        findings = []
        for eid, fn, ln, dept, r_id, l_id, loc_id in employees:
            sal = latest_sals.get(eid)
            if sal is None:
                continue

            cohort_key = f"{r_id}::{l_id}::{loc_id}"
            med_sal = cohort_medians.get(cohort_key, sal)
            size = cohort_sizes.get(cohort_key, 1)

            band = band_lookup.get((r_id, l_id, loc_id))
            if band:
                b_min, b_mid, b_max = get_band_usd_amounts(band, curr_norm)
            else:
                b_min, b_mid, b_max = med_sal * 0.8, med_sal, med_sal * 1.2

            rating = latest_perf[eid][0] if eid in latest_perf else None
            c_tenure, r_tenure = tenures.get(eid, (1.0, 1.0))

            res = detector.evaluate_employee(
                employee_id=eid,
                normalized_salary=sal,
                band_min=b_min,
                band_mid=b_mid,
                band_max=b_max,
                cohort_median_salary=med_sal,
                cohort_size=size,
                performance_rating=rating,
                tenure_in_role_years=r_tenure,
                tenure_in_company_years=c_tenure
            )

            findings.append({
                "Employee ID": eid,
                "Name": f"{fn} {ln}",
                "Department": dept,
                "Role": role_map.get(r_id, r_id),
                "Level": level_map.get(l_id, l_id),
                "Location": loc_map.get(loc_id, loc_id),
                "Salary (USD)": sal,
                "Cohort Median": med_sal,
                "Deviation (%)": float(res.deviation_from_cohort_median_pct),
                "Compa-Ratio": float(res.compa_ratio),
                "Rating": rating,
                "Company Tenure (yrs)": round(c_tenure, 1),
                "Status": _STATUS_LABELS.get(res.status, res.status),
                "Primary Reason": res.primary_reason,
                "Is Disparity": "Yes" if res.is_disparity else "No",
                "_role_id": r_id,
                "_level_id": l_id,
                "_location_id": loc_id,
            })

        return pd.DataFrame(findings)
    finally:
        db.close()


def render(db: Session, selected_role: str, selected_level: str, selected_location: str):
    st.header("Multi-Factor Disparity Detection & Evidence Analysis")
    st.markdown("Identifies unexplained compensation disparities benchmarked against peer cohort medians, documented performance ratings, and tenure.")

    df = _load_disparity_findings()
    if not df.empty:
        if selected_role != "All":
            df = df[df["_role_id"] == selected_role]
        if selected_level != "All":
            df = df[df["_level_id"] == selected_level]
        if selected_location != "All":
            df = df[df["_location_id"] == selected_location]

    if df.empty:
        st.info("No employee records available for disparity evaluation.")
        return

    unexplained_count = int((df["Status"] == "Unexplained Disparity").sum())
    review_count = int((df["Status"] == "Manual Review Required").sum())
    explained_count = int((df["Status"] == "Explained Variation").sum())
    insufficient_count = int((df["Status"] == "Insufficient Evidence").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unexplained Disparities", f"{unexplained_count:,}", delta=f"{unexplained_count} flagged", delta_color="inverse")
    col2.metric("Manual Review Required", f"{review_count:,}", "Mixed signals detected")
    col3.metric("Explained Variations", f"{explained_count:,}", "Supported by merit or tenure")
    col4.metric("Insufficient Evidence", f"{insufficient_count:,}", "Cohort too small to conclude")

    st.markdown("---")

    col_pie, col_scatter = st.columns(2)
    with col_pie:
        status_dist = df["Status"].value_counts().reset_index()
        status_dist.columns = ["Status", "Count"]
        fig_pie = px.pie(
            status_dist,
            names="Status",
            values="Count",
            hole=0.42,
            title="Compensation Equity Evaluation Classification",
            color="Status",
            color_discrete_map=_STATUS_COLORS,
        )
        fig_pie.update_traces(
            textinfo="percent+value",
            marker=dict(line=dict(color="#0f172a", width=2)),
        )
        apply_clean_layout(fig_pie, legend_bottom=True, height=460, legend_position="bottom")
        st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)

    with col_scatter:
        df_scatter = df[(df["Deviation (%)"] >= -80.0) & (df["Deviation (%)"] <= 150.0)].copy()
        fig_disp = px.scatter(
            df_scatter,
            x="Rating",
            y="Deviation (%)",
            color="Status",
            hover_data=["Employee ID", "Name", "Salary (USD)"],
            title="Performance Rating vs Cohort Deviation (%)",
            color_discrete_map=_STATUS_COLORS,
        )
        fig_disp.add_hline(
            y=-15.0, line_dash="dash", line_color="#e74c3c",
            annotation_text="Disparity Threshold (-15%)", annotation_position="bottom right"
        )
        fig_disp.add_vline(
            x=3.5, line_dash="dash", line_color="#3498db",
            annotation_text="High Performer (3.5+)", annotation_position="top right", annotation_yshift=-6
        )
        apply_clean_layout(fig_disp, legend_bottom=True, height=460)
        st.plotly_chart(fig_disp, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Disparity Evaluation Findings")

    # Table filters placed directly above Disparity Evaluation Findings
    flagged_rows = df[df["Is Disparity"] == "Yes"]
    flagged_opts = ["None (Use Search / Filters Below)"] + [
        f"{r['Employee ID']} — {r['Name']} ({r['Role']} · {r['Level']} · {r['Location']})"
        for _, r in flagged_rows.iterrows()
    ]
    flagged_id_map = {
        f"{r['Employee ID']} — {r['Name']} ({r['Role']} · {r['Level']} · {r['Location']})": r["Employee ID"]
        for _, r in flagged_rows.iterrows()
    }

    selected_flagged_label = st.selectbox(
        "Quick Compare — Select a Flagged Employee to Compare with Cohort Peers:",
        flagged_opts,
        index=0,
    )

    dept_opts = ["All Departments"] + sorted(df["Department"].unique().tolist())
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.8, 1.5, 1.3])
    with f_col1:
        emp_search = st.text_input(
            "Filter by Employee ID or Name:",
            "",
            placeholder="e.g. EMP-000093 or Jane Smith",
        )
    with f_col2:
        status_filter = st.selectbox(
            "Analytical Disparity Classification:",
            ["All Outcomes", "Unexplained Disparity", "Manual Review Required", "Explained Variation", "Insufficient Evidence"],
            index=0
        )
    with f_col3:
        dept_filter = st.selectbox("Department:", dept_opts, index=0)
    with f_col4:
        flagged_only = st.checkbox("Flagged Only", value=False)
        include_peers = st.checkbox(
            "Include Cohort Peers",
            value=(selected_flagged_label != "None (Use Search / Filters Below)"),
        )

    from src.database.models import ReviewCase as _ReviewCase
    _case_map = {c.employee_id: c.status for c in db.query(_ReviewCase).all()}
    df["Review Case Status"] = df["Employee ID"].map(lambda eid: _case_map.get(eid, "OPEN"))

    case_status_filter = st.selectbox(
        "Filter by Human Review Case Status (Workflow State — distinct from Analytical Classification above):",
        ["All Case Statuses", "OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "REOPENED"],
        index=0,
        key="disp_case_status_filter",
    )

    filtered = df.copy()
    if case_status_filter != "All Case Statuses":
        filtered = filtered[filtered["Review Case Status"] == case_status_filter]
    if dept_filter != "All Departments":
        filtered = filtered[filtered["Department"] == dept_filter]

    if selected_flagged_label != "None (Use Search / Filters Below)":
        target_id = flagged_id_map[selected_flagged_label]
        match_mask = filtered["Employee ID"] == target_id
        if include_peers and match_mask.any():
            cohort_pairs = set(zip(
                filtered.loc[match_mask, "_role_id"],
                filtered.loc[match_mask, "_level_id"],
                filtered.loc[match_mask, "_location_id"],
            ))
            peer_mask = filtered.apply(
                lambda r: (r["_role_id"], r["_level_id"], r["_location_id"]) in cohort_pairs,
                axis=1,
            )
            filtered = filtered[peer_mask]
        else:
            filtered = filtered[match_mask]
    elif emp_search.strip():
        q = emp_search.strip().lower()
        match_mask = (
            filtered["Employee ID"].str.lower().str.contains(q, na=False)
            | filtered["Name"].str.lower().str.contains(q, na=False)
        )
        if include_peers and match_mask.any():
            cohort_pairs = set(
                zip(
                    filtered.loc[match_mask, "_role_id"],
                    filtered.loc[match_mask, "_level_id"],
                    filtered.loc[match_mask, "_location_id"],
                )
            )
            peer_mask = filtered.apply(
                lambda r: (r["_role_id"], r["_level_id"], r["_location_id"]) in cohort_pairs,
                axis=1,
            )
            filtered = filtered[peer_mask]
        else:
            filtered = filtered[match_mask]

    if status_filter != "All Outcomes":
        filtered = filtered[filtered["Status"] == status_filter]
    if flagged_only:
        filtered = filtered[filtered["Is Disparity"] == "Yes"]

    if filtered.empty:
        st.info("No employee disparity records match the current filters.")
        return

    st.caption(f"Showing {len(filtered):,} employee record(s)")
    disp_table = pd.DataFrame({
        "Employee ID": filtered["Employee ID"],
        "Name": filtered["Name"],
        "Department": filtered["Department"],
        "Role": filtered["Role"],
        "Level": filtered["Level"],
        "Location": filtered["Location"],
        "Salary (USD)": filtered["Salary (USD)"].map(fmt_usd),
        "Cohort Median": filtered["Cohort Median"].map(fmt_usd),
        "Deviation (%)": filtered["Deviation (%)"].map(lambda v: fmt_pct(v, 1, signed=True)),
        "Compa-Ratio": filtered["Compa-Ratio"],
        "Rating": filtered["Rating"],
        "Tenure (yrs)": filtered["Company Tenure (yrs)"],
        "Status": filtered["Status"],
        "Review Case Status": filtered["Review Case Status"],
        "Is Disparity": filtered["Is Disparity"],
        "Primary Reason": filtered["Primary Reason"],
    })
    st.dataframe(
        disp_table,
        use_container_width=True,
        hide_index=True,
        column_config=build_table_column_config(
            disp_table,
            overrides={
                "Compa-Ratio": st.column_config.NumberColumn("Compa-Ratio", format="%.2f"),
                "Rating": st.column_config.NumberColumn("Rating", format="%.2f"),
                "Tenure (yrs)": st.column_config.NumberColumn("Tenure (yrs)", format="%.1f"),
            },
        ),
    )

    st.markdown("---")
    with st.expander("Review Case Management (Human Review Workflow)", expanded=False):
        st.info("Note: A disparity flag is a statistical indicator requesting human review — never automatic proof of discrimination.")
        from src.database.models import ReviewCase
        from src.workflow.audit_logger import AuditLogger

        flagged_ids = flagged_rows["Employee ID"].tolist()
        if not flagged_ids:
            st.write("No flagged employees in current filter.")
        else:
            rc_emp = st.selectbox("Select Flagged Employee for Case Action:", flagged_ids, key="rc_emp_sel")
            existing_case = db.query(ReviewCase).filter(ReviewCase.employee_id == rc_emp).first()
            cur_status = existing_case.status if existing_case else "OPEN"
            st.caption(f"Current Case Status: **{cur_status}** | Assigned To: **{existing_case.assigned_to if existing_case and existing_case.assigned_to else 'Unassigned'}**")

            rc1, rc2 = st.columns(2)
            with rc1:
                new_status = st.selectbox(
                    "Transition Case Status:",
                    ["OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "REOPENED"],
                    index=["OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "REOPENED"].index(cur_status) if cur_status in ["OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "REOPENED"] else 0,
                    key="rc_status_sel",
                )
                assignee = st.text_input("Assign / Escalate To:", value=(existing_case.assigned_to or "hr.partner@company.org") if existing_case else "hr.partner@company.org", key="rc_assignee")
            with rc2:
                comments = st.text_area("Reviewer Investigation Comments:", value=(existing_case.comments or "") if existing_case else "", key="rc_comments")

            if st.button("Save Review Case Update", key="rc_save_btn", type="primary"):
                case_id = f"CASE-{rc_emp}"
                if not existing_case:
                    existing_case = ReviewCase(
                        case_id=case_id,
                        employee_id=rc_emp,
                        status=new_status,
                        assigned_to=assignee.strip() or None,
                        comments=comments.strip() or None,
                    )
                    db.add(existing_case)
                    old_s = None
                else:
                    old_s = existing_case.status
                    existing_case.status = new_status
                    existing_case.assigned_to = assignee.strip() or None
                    existing_case.comments = comments.strip() or None
                AuditLogger.log_event(
                    session=db,
                    entity_name="ReviewCase",
                    entity_id=case_id,
                    event_type="REVIEW_CASE_UPDATED",
                    actor_id=assignee.strip() or "HR_REVIEWER",
                    actor_role="HR_PARTNER",
                    old_state={"status": old_s} if old_s else None,
                    new_state={"status": new_status, "assigned_to": assignee},
                    notes=comments.strip() or "Updated review case.",
                )
                db.commit()
                st.success(f"Review case {case_id} updated to {new_status} and logged to audit history.")
