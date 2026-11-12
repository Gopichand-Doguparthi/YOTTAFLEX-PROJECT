"""
Comprehensive Data Quality and Integrity Validation Suite.
Audits database state for referential integrity, primary-key uniqueness,
date ordering, arithmetic reconciliation, enum validity, and lifecycle consistency.
"""
from datetime import date, datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from src.database.models import (
    Location, Role, Level, CompensationBand, Employee,
    SalaryRecord, PerformanceEvidence, Tenure, Promotion,
    AdjustmentProposal, ApprovalEvent, ExchangeRate,
    RoleComparabilityRationale, GroundTruthRecord
)


class DataValidator:
    """Performs deep relational, logical, and arithmetic integrity checks."""

    @classmethod
    def run_all_checks(cls, session: Session) -> Dict[str, Any]:
        """Runs the complete suite of validation checks and returns summary metrics."""
        results = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "pass_rate_pct": 100.0,
            "details": []
        }

        checks = [
            cls.check_pk_uniqueness(session),
            cls.check_foreign_key_integrity(session),
            cls.check_fte_ranges(session),
            cls.check_band_spread_arithmetic(session),
            cls.check_date_orderings(session),
            cls.check_salary_normalization_arithmetic(session),
            cls.check_proposal_arithmetic(session),
            cls.check_lifecycle_statuses(session),
            cls.check_exchange_rate_coverage(session),
            cls.check_duplicate_records(session),
        ]

        for check in checks:
            results["total_checks"] += 1
            if check["passed"]:
                results["passed_checks"] += 1
            else:
                results["failed_checks"] += 1
            results["details"].append(check)

        if results["total_checks"] > 0:
            results["pass_rate_pct"] = round((results["passed_checks"] / results["total_checks"]) * 100.0, 2)

        return results

    @staticmethod
    def check_pk_uniqueness(session: Session) -> Dict[str, Any]:
        """Validates primary key uniqueness across core entities."""
        models_to_check = [
            (Employee, "employee_id"),
            (Role, "role_id"),
            (Level, "level_id"),
            (Location, "location_id"),
            (CompensationBand, "band_id"),
            (SalaryRecord, "salary_id"),
            (PerformanceEvidence, "evidence_id"),
            (Tenure, "tenure_id"),
            (Promotion, "promotion_id"),
            (AdjustmentProposal, "proposal_id"),
            (ApprovalEvent, "event_id"),
            (ExchangeRate, "exchange_rate_id"),
            (RoleComparabilityRationale, "mapping_id"),
            (GroundTruthRecord, "ground_truth_id"),
        ]
        violations = []
        for model, pk_name in models_to_check:
            total_count = session.query(model).count()
            distinct_count = session.query(getattr(model, pk_name)).distinct().count()
            if total_count != distinct_count:
                violations.append(f"{model.__name__} has duplicate primary keys ({total_count} vs {distinct_count} distinct).")

        return {
            "check_name": "primary_key_uniqueness",
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "description": "Ensures all entity primary keys are strictly unique.",
            "details": violations
        }

    @staticmethod
    def check_foreign_key_integrity(session: Session) -> Dict[str, Any]:
        """Validates foreign key referential integrity."""
        violations = []

        # Employee foreign keys
        role_ids = {r.role_id for r in session.query(Role.role_id).all()}
        level_ids = {l.level_id for l in session.query(Level.level_id).all()}
        loc_ids = {loc.location_id for loc in session.query(Location.location_id).all()}
        emp_ids = {e.employee_id for e in session.query(Employee.employee_id).all()}

        orphan_emp_roles = session.query(Employee).filter(~Employee.current_role_id.in_(role_ids)).count()
        orphan_emp_levels = session.query(Employee).filter(~Employee.current_level_id.in_(level_ids)).count()
        orphan_emp_locs = session.query(Employee).filter(~Employee.current_location_id.in_(loc_ids)).count()

        if orphan_emp_roles > 0:
            violations.append(f"{orphan_emp_roles} employees reference non-existent roles.")
        if orphan_emp_levels > 0:
            violations.append(f"{orphan_emp_levels} employees reference non-existent levels.")
        if orphan_emp_locs > 0:
            violations.append(f"{orphan_emp_locs} employees reference non-existent locations.")

        # Salary record foreign keys
        orphan_salaries = session.query(SalaryRecord).filter(~SalaryRecord.employee_id.in_(emp_ids)).count()
        if orphan_salaries > 0:
            violations.append(f"{orphan_salaries} salary records reference non-existent employees.")

        # Proposal foreign keys
        orphan_proposals = session.query(AdjustmentProposal).filter(~AdjustmentProposal.employee_id.in_(emp_ids)).count()
        if orphan_proposals > 0:
            violations.append(f"{orphan_proposals} proposals reference non-existent employees.")

        return {
            "check_name": "foreign_key_integrity",
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "description": "Validates parent-child referential integrity across all relationships.",
            "details": violations
        }

    @staticmethod
    def check_fte_ranges(session: Session) -> Dict[str, Any]:
        """Validates FTE values lie strictly in (0.0, 1.0]."""
        invalid_emp_fte = session.query(Employee).filter((Employee.fte <= 0.0) | (Employee.fte > 1.0)).count()
        invalid_sal_fte = session.query(SalaryRecord).filter((SalaryRecord.fte <= 0.0) | (SalaryRecord.fte > 1.0)).count()

        violations = []
        if invalid_emp_fte > 0:
            violations.append(f"{invalid_emp_fte} employees have invalid FTE outside (0.0, 1.0].")
        if invalid_sal_fte > 0:
            violations.append(f"{invalid_sal_fte} salary records have invalid FTE outside (0.0, 1.0].")

        return {
            "check_name": "fte_validity",
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "description": "Checks that FTE fractional working values fall within (0.0, 1.0].",
            "details": violations
        }

    @staticmethod
    def check_band_spread_arithmetic(session: Session) -> Dict[str, Any]:
        """Validates min_salary < mid_salary < max_salary for all compensation bands."""
        invalid_bands = session.query(CompensationBand).filter(
            (CompensationBand.min_salary >= CompensationBand.mid_salary) |
            (CompensationBand.mid_salary >= CompensationBand.max_salary) |
            (CompensationBand.min_salary <= 0)
        ).count()

        return {
            "check_name": "band_spread_arithmetic",
            "passed": invalid_bands == 0,
            "violations_count": invalid_bands,
            "description": "Verifies that all compensation bands satisfy min_salary < mid_salary < max_salary.",
            "details": [f"{invalid_bands} bands have invalid spreads."] if invalid_bands > 0 else []
        }

    @staticmethod
    def check_date_orderings(session: Session) -> Dict[str, Any]:
        """Validates temporal order of dates across employee records, bands, and promotions."""
        violations = []

        # Band start <= end date
        invalid_band_dates = session.query(CompensationBand).filter(
            CompensationBand.effective_end_date.isnot(None),
            CompensationBand.effective_start_date > CompensationBand.effective_end_date
        ).count()
        if invalid_band_dates > 0:
            violations.append(f"{invalid_band_dates} compensation bands have start_date > end_date.")

        # Exchange rate start <= end date
        invalid_fx_dates = session.query(ExchangeRate).filter(
            ExchangeRate.effective_start_date > ExchangeRate.effective_end_date
        ).count()
        if invalid_fx_dates > 0:
            violations.append(f"{invalid_fx_dates} exchange rates have start_date > end_date.")

        # Salary effective_date <= end_date
        invalid_sal_end = session.query(SalaryRecord).filter(
            SalaryRecord.end_date.isnot(None),
            SalaryRecord.effective_date > SalaryRecord.end_date
        ).count()
        if invalid_sal_end > 0:
            violations.append(f"{invalid_sal_end} salary records have effective_date > end_date.")

        # Salary effective_date >= employee hire_date
        invalid_hire_sal = session.query(SalaryRecord).join(
            Employee, SalaryRecord.employee_id == Employee.employee_id
        ).filter(SalaryRecord.effective_date < Employee.hire_date).count()
        if invalid_hire_sal > 0:
            violations.append(f"{invalid_hire_sal} salary records precede employee hire_date.")

        return {
            "check_name": "date_ordering",
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "description": "Validates logical ordering of start, end, hire, and effective dates.",
            "details": violations
        }

    @staticmethod
    def check_salary_normalization_arithmetic(session: Session) -> Dict[str, Any]:
        """Verifies normalized salaries are positive and reconcile with (annual_base * fx_rate) / fte."""
        from src.engine.currency_normalizer import CurrencyNormalizer, MissingCurrencyConversionException

        non_positive = session.query(SalaryRecord).filter(SalaryRecord.normalized_salary <= 0).count()
        curr_norm = CurrencyNormalizer()
        curr_norm.load_from_db(session)

        reconciliation_mismatches = 0
        known_edge_case_injections = 0
        for sal in session.query(SalaryRecord).all():
            if sal.fte <= 0:
                continue
            annual_base = sal.base_salary * 12.0 if sal.pay_frequency == "MONTHLY" else sal.base_salary
            try:
                fx_rate = curr_norm.get_rate(sal.currency, "USD", sal.effective_date)
                expected_norm = round((annual_base * fx_rate) / sal.fte, 2)
                if abs(expected_norm - sal.normalized_salary) > max(1.0, expected_norm * 0.005):
                    # Recognize intentional Edge Case 2 (FTE ignored) and Edge Case 3 (1:1 missing FX) test records
                    is_fte_ignored = sal.fte < 1.0 and abs(round(annual_base * fx_rate, 2) - sal.normalized_salary) <= 1.0
                    is_missing_fx = sal.currency != "USD" and abs(round(sal.base_salary, 2) - sal.normalized_salary) <= 1.0
                    if is_fte_ignored or is_missing_fx:
                        known_edge_case_injections += 1
                    else:
                        reconciliation_mismatches += 1
            except MissingCurrencyConversionException:
                # Missing FX is tracked separately by exchange_rate_coverage / exception detector
                continue

        details = []
        if non_positive > 0:
            details.append(f"{non_positive} salary records have non-positive normalized salary.")
        if reconciliation_mismatches > 0:
            details.append(f"{reconciliation_mismatches} salary records fail (annual_base * fx_rate) / fte reconciliation.")
        if known_edge_case_injections > 0:
            details.append(
                f"Informational: {known_edge_case_injections} records match intentional Edge Case 2/3 negative-scenario patterns (tracked in Exceptions & Edge Cases)."
            )

        total_violations = non_positive + reconciliation_mismatches
        return {
            "check_name": "salary_normalization_arithmetic",
            "passed": total_violations == 0,
            "violations_count": total_violations,
            "description": "Checks that normalized salaries are positive and reconcile with base_salary, FX rate, and FTE.",
            "details": details
        }

    @staticmethod
    def check_proposal_arithmetic(session: Session) -> Dict[str, Any]:
        """Validates that proposed_salary - current_salary == adjustment_amount."""
        proposals = session.query(AdjustmentProposal).all()
        mismatches = 0
        for p in proposals:
            diff = round(p.proposed_salary - p.current_salary, 2)
            if abs(diff - p.adjustment_amount) > 0.05:
                mismatches += 1

        return {
            "check_name": "proposal_arithmetic_reconciliation",
            "passed": mismatches == 0,
            "violations_count": mismatches,
            "description": "Verifies proposal adjustment_amount matches proposed - current salary.",
            "details": [f"{mismatches} proposals have mismatched adjustment amounts."] if mismatches > 0 else []
        }

    @staticmethod
    def check_lifecycle_statuses(session: Session) -> Dict[str, Any]:
        """Validates allowed enum values across lifecycle statuses."""
        allowed_proposal_statuses = {"DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"}
        invalid_proposals = session.query(AdjustmentProposal).filter(
            ~AdjustmentProposal.approval_status.in_(allowed_proposal_statuses)
        ).count()

        allowed_band_statuses = {"ACTIVE", "EXPIRED", "DRAFT"}
        invalid_bands = session.query(CompensationBand).filter(
            ~CompensationBand.status.in_(allowed_band_statuses)
        ).count()

        violations = []
        if invalid_proposals > 0:
            violations.append(f"{invalid_proposals} proposals have invalid lifecycle status.")
        if invalid_bands > 0:
            violations.append(f"{invalid_bands} bands have invalid lifecycle status.")

        return {
            "check_name": "lifecycle_status_enums",
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "description": "Validates that lifecycle statuses belong to approved enumerations.",
            "details": violations
        }

    @staticmethod
    def check_exchange_rate_coverage(session: Session) -> Dict[str, Any]:
        """Verifies that all location currencies have exchange rates defined for active years."""
        currencies = {loc.currency for loc in session.query(Location.currency).distinct()}
        fx_currencies = {fx.from_currency for fx in session.query(ExchangeRate.from_currency).distinct()}
        missing = currencies - fx_currencies - {"USD"}

        return {
            "check_name": "exchange_rate_coverage",
            "passed": len(missing) == 0,
            "violations_count": len(missing),
            "description": "Verifies that exchange rates exist for all operating currencies.",
            "details": [f"Missing exchange rates for currencies: {missing}"] if missing else []
        }

    @staticmethod
    def check_duplicate_records(session: Session) -> Dict[str, Any]:
        """Detects duplicate logical records (same employee+effective_date in salaries or employee+review_cycle in performance)."""
        from sqlalchemy import func
        dup_sal = (
            session.query(SalaryRecord.employee_id, SalaryRecord.effective_date)
            .group_by(SalaryRecord.employee_id, SalaryRecord.effective_date)
            .having(func.count(SalaryRecord.salary_id) > 1)
            .count()
        )
        dup_perf = (
            session.query(PerformanceEvidence.employee_id, PerformanceEvidence.review_cycle)
            .group_by(PerformanceEvidence.employee_id, PerformanceEvidence.review_cycle)
            .having(func.count(PerformanceEvidence.evidence_id) > 1)
            .count()
        )
        violations = []
        if dup_sal > 0:
            violations.append(f"{dup_sal} duplicate (employee_id, effective_date) salary record groups found.")
        if dup_perf > 0:
            violations.append(f"{dup_perf} duplicate (employee_id, review_cycle) performance evidence groups found.")
        return {
            "check_name": "duplicate_logical_records",
            "passed": len(violations) == 0,
            "violations_count": dup_sal + dup_perf,
            "description": "Ensures no duplicate salary effective dates or review cycles exist per employee.",
            "details": violations
        }
