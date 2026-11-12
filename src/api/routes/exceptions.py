"""
Operational Exceptions and Negative Scenarios API Endpoints.
Covers the Five Mandatory Edge Cases.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import (
    SalaryRecord, CompensationBand, Employee, AdjustmentProposal,
    ApprovalEvent, RoleComparabilityRationale
)
from src.engine.currency_normalizer import CurrencyNormalizer
from src.engine.comparable_groups import ComparableGroupEngine
from src.engine.exception_detector import ExceptionDetector

router = APIRouter(prefix="/exceptions", tags=["Exceptions & Negative Scenarios"])


@router.get("")
def list_detected_exceptions(
    issue_type: Optional[str] = Query(None, description="Filter by issue type"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Detects operational exceptions and negative scenarios across active records."""
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

        # Check 3: Missing currency conversion
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
            else:
                exc_curr = detector.check_currency_conversion(sal.currency, sal.effective_date)
                if exc_curr:
                    exc_curr["record_id"] = sal.salary_id
                    exc_curr["employee_id"] = sal.employee_id
                    exceptions.append(exc_curr)

        # Check 4: Unapproved adjustment applied
        if sal.change_reason == "EQUITY_CORRECTION":
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

    # Check 5: Incomparable roles flagged in operational comparability rationales (no ground-truth leakage)
    incomp_rationales = db.query(RoleComparabilityRationale).filter_by(is_comparable=False).all()
    for rcr in incomp_rationales:
        exc_grp = detector.check_incomparable_roles_grouped(rcr.role_id_a, rcr.role_id_b)
        if exc_grp:
            exc_grp["record_id"] = f"GRP-{rcr.role_id_a}-{rcr.role_id_b}"
            exc_grp["employee_id"] = "N/A (Cohort Level)"
            exceptions.append(exc_grp)

    # Apply filter if requested
    if issue_type:
        exceptions = [e for e in exceptions if e["issue_type"] == issue_type]

    return {
        "total_exceptions": len(exceptions),
        "exceptions": exceptions[:limit]
    }
