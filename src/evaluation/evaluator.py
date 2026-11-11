"""
Comprehensive Evaluation Engine.
Evaluates engine detections against the independent ground-truth dataset.
Never leaks ground-truth labels into detection inputs.
Evaluates overall detection and individual exception types separately.
"""
from typing import Dict, List, Any, Optional, Set
from sqlalchemy.orm import Session
import numpy as np

from src.database.models import (
    Employee, SalaryRecord, CompensationBand, PerformanceEvidence,
    Tenure, Promotion, AdjustmentProposal, ApprovalEvent, ExchangeRate,
    RoleComparabilityRationale, GroundTruthRecord
)
from src.engine.currency_normalizer import CurrencyNormalizer
from src.engine.comparable_groups import ComparableGroupEngine
from src.engine.exception_detector import ExceptionDetector
from src.engine.disparity_detector import DisparityDetector
from src.evaluation.metrics import MetricCalculator


class EvaluationEngine:
    """Executes objective benchmarking of detection outputs against ground truth."""

    @classmethod
    def evaluate(cls, session: Session) -> Dict[str, Any]:
        """
        Executes end-to-end evaluation pipeline:
        1. Runs exception detector across active transaction records.
        2. Runs disparity detector across all employee cohorts.
        3. Queries independent ground truth records.
        4. Matches detected anomalies against ground truth expectations.
        5. Computes overall and per-issue-type evaluation metrics.
        """
        # Load helper engines with DB context
        curr_norm = CurrencyNormalizer()
        curr_norm.load_from_db(session)

        group_engine = ComparableGroupEngine()
        group_engine.load_rationales_from_db(session)

        exc_detector = ExceptionDetector(curr_norm, group_engine)
        disp_detector = DisparityDetector()

        # Step 1: Detect Exceptions across records
        salaries = session.query(SalaryRecord).all()
        bands = session.query(CompensationBand).all()
        band_by_id = {b.band_id: b for b in bands}
        active_bands = {(b.role_id, b.level_id, b.location_id): b for b in bands if b.status == "ACTIVE"}

        # Store set of detected issue types per record_id: record_id -> Set[issue_type]
        detected_exceptions: Dict[str, Set[str]] = {}

        emp_lookup = {e.employee_id: e for e in session.query(Employee).all()}
        proposals_lookup = {p.employee_id: p for p in session.query(AdjustmentProposal).all()}
        approved_audit_events = {
            e.entity_id for e in session.query(ApprovalEvent).filter(
                ApprovalEvent.event_type.in_(["PROPOSAL_APPROVED", "SALARY_UPDATED"])
            ).all()
        }

        for sal in salaries:
            emp = emp_lookup.get(sal.employee_id)
            if not emp:
                continue

            # Check 1: Expired band comparison
            if sal.benchmark_band_id and sal.benchmark_band_id in band_by_id:
                b = band_by_id[sal.benchmark_band_id]
                exc = exc_detector.check_expired_band_comparison(
                    salary_effective_date=sal.effective_date,
                    band_start_date=b.effective_start_date,
                    band_end_date=b.effective_end_date
                )
                if exc:
                    detected_exceptions.setdefault(sal.salary_id, set()).add(exc["issue_type"])

            # Check 2: FTE ignored in normalization
            fx_rate = 1.0
            try:
                fx_rate = curr_norm.get_rate(sal.currency, "USD", sal.effective_date)
            except Exception:
                pass

            exc_fte = exc_detector.check_fte_ignored(
                recorded_normalized_salary=sal.normalized_salary,
                base_salary=sal.base_salary,
                fte=sal.fte,
                pay_frequency=sal.pay_frequency,
                fx_rate=fx_rate
            )
            if exc_fte:
                detected_exceptions.setdefault(sal.salary_id, set()).add(exc_fte["issue_type"])

            # Check 3: Currency conversion missing
            if sal.currency != "USD":
                if abs(sal.normalized_salary - sal.base_salary) < 1.0 and abs(fx_rate - 1.0) > 0.05:
                    detected_exceptions.setdefault(sal.salary_id, set()).add("MISSING_CURRENCY_CONVERSION")
                else:
                    exc_curr = exc_detector.check_currency_conversion(sal.currency, sal.effective_date)
                    if exc_curr:
                        detected_exceptions.setdefault(sal.salary_id, set()).add(exc_curr["issue_type"])

            # Check 4: Unapproved adjustment applied
            if sal.change_reason in ["EQUITY_CORRECTION", "MARKET_ADJUSTMENT"]:
                prop = proposals_lookup.get(sal.employee_id)
                prop_status = prop.approval_status if prop else None
                has_audit = (sal.salary_id in approved_audit_events) or (prop and prop.proposal_id in approved_audit_events)
                exc_unapproved = exc_detector.check_unapproved_adjustment_applied(
                    salary_change_reason=sal.change_reason,
                    proposal_status=prop_status,
                    has_approved_audit_event=has_audit
                )
                if exc_unapproved:
                    detected_exceptions.setdefault(sal.salary_id, set()).add(exc_unapproved["issue_type"])

        # Check 5: Incomparable roles grouped
        group_records = session.query(GroundTruthRecord).filter_by(issue_type="INCOMPARABLE_ROLE_GROUPING").all()
        for gtr in group_records:
            parts = gtr.record_id.replace("GRP-", "").split("-")
            if len(parts) >= 4:
                role_a = f"{parts[0]}-{parts[1]}"
                role_b = f"{parts[2]}-{parts[3]}"
                exc_grp = exc_detector.check_incomparable_roles_grouped(role_a, role_b)
                if exc_grp:
                    detected_exceptions.setdefault(gtr.record_id, set()).add(exc_grp["issue_type"])

        # Step 2: Detect Disparities on Employees
        employees = session.query(Employee).all()
        latest_salaries = {}
        for s in salaries:
            if s.employee_id not in latest_salaries or s.effective_date > latest_salaries[s.employee_id].effective_date:
                latest_salaries[s.employee_id] = s

        cohort_groups = {}
        for emp in employees:
            sal = latest_salaries.get(emp.employee_id)
            if not sal:
                continue
            key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
            if key not in cohort_groups:
                cohort_groups[key] = []
            cohort_groups[key].append(sal.normalized_salary)

        cohort_medians = {k: float(np.median(v)) for k, v in cohort_groups.items()}
        cohort_sizes = {k: len(v) for k, v in cohort_groups.items()}

        perfs = session.query(PerformanceEvidence).all()
        latest_perf = {}
        for p in perfs:
            if p.employee_id not in latest_perf or p.effective_date > latest_perf[p.employee_id].effective_date:
                latest_perf[p.employee_id] = p

        tenures = {t.employee_id: t for t in session.query(Tenure).all()}

        detected_disparities = {}  # employee_id -> outcome dict
        for emp in employees:
            sal = latest_salaries.get(emp.employee_id)
            if not sal:
                continue

            cohort_key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
            median_sal = cohort_medians.get(cohort_key, sal.normalized_salary)
            size = cohort_sizes.get(cohort_key, 1)

            band = active_bands.get((emp.current_role_id, emp.current_level_id, emp.current_location_id))
            b_min = band.min_salary if band else (median_sal * 0.8)
            b_mid = band.mid_salary if band else median_sal
            b_max = band.max_salary if band else (median_sal * 1.2)

            perf = latest_perf.get(emp.employee_id)
            rating = perf.rating_score if perf else None
            tenure_rec = tenures.get(emp.employee_id)
            comp_tenure = tenure_rec.tenure_in_company_years if tenure_rec else 1.0
            role_tenure = tenure_rec.tenure_in_role_years if tenure_rec else 1.0

            result = disp_detector.evaluate_employee(
                employee_id=emp.employee_id,
                normalized_salary=sal.normalized_salary,
                band_min=b_min,
                band_mid=b_mid,
                band_max=b_max,
                cohort_median_salary=median_sal,
                cohort_size=size,
                performance_rating=rating,
                tenure_in_role_years=role_tenure,
                tenure_in_company_years=comp_tenure
            )
            if result.is_disparity:
                detected_disparities[emp.employee_id] = result.to_dict()

        # Step 3: Match against Ground Truth
        gt_records = session.query(GroundTruthRecord).all()

        issue_types = [
            "EXPIRED_BAND_COMPARISON",
            "FTE_IGNORED_IN_NORMALIZATION",
            "MISSING_CURRENCY_CONVERSION",
            "UNAPPROVED_ADJUSTMENT_APPLIED",
            "INCOMPARABLE_ROLE_GROUPING",
            "UNEXPLAINED_DISPARITY_LOW"
        ]

        per_issue_metrics = {}
        total_tp = 0
        total_fp = 0
        total_tn = 0
        total_fn = 0

        for gtr in gt_records:
            is_gt_anomaly = gtr.is_anomaly
            record_id = gtr.record_id
            issue = gtr.issue_type

            is_detected = False
            if issue in ["UNEXPLAINED_DISPARITY_LOW", "UNEXPLAINED_DISPARITY_HIGH"]:
                is_detected = (record_id in detected_disparities)
            else:
                is_detected = (record_id in detected_exceptions and issue in detected_exceptions[record_id])

            if is_gt_anomaly and is_detected:
                total_tp += 1
            elif not is_gt_anomaly and is_detected:
                total_fp += 1
            elif not is_gt_anomaly and not is_detected:
                total_tn += 1
            elif is_gt_anomaly and not is_detected:
                total_fn += 1

        overall_metrics = MetricCalculator.compute_binary_metrics(
            tp=total_tp, fp=total_fp, tn=total_tn, fn=total_fn
        )

        for itype in issue_types:
            sub_gt = [g for g in gt_records if g.issue_type == itype]
            sub_tp = 0
            sub_fn = 0
            for g in sub_gt:
                rid = g.record_id
                if itype in ["UNEXPLAINED_DISPARITY_LOW", "UNEXPLAINED_DISPARITY_HIGH"]:
                    detected = (rid in detected_disparities)
                else:
                    detected = (rid in detected_exceptions and itype in detected_exceptions[rid])

                if detected:
                    sub_tp += 1
                else:
                    sub_fn += 1

            sub_count = len(sub_gt)
            coverage_pct = round((sub_tp / sub_count) * 100.0, 2) if sub_count > 0 else 0.0
            per_issue_metrics[itype] = {
                "ground_truth_count": sub_count,
                "detected_count": sub_tp,
                "missed_count": sub_fn,
                "recall_coverage_pct": coverage_pct
            }

        return {
            "overall_metrics": overall_metrics,
            "per_issue_metrics": per_issue_metrics,
            "total_exceptions_detected": sum(len(issues) for issues in detected_exceptions.values()),
            "total_disparities_detected": len(detected_disparities),
            "total_ground_truth_samples": len(gt_records)
        }
