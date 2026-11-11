"""
Exception Detection Module for the Five Mandatory Edge Cases and Operational Anomalies.
Provides deterministic validation and error diagnostics.
"""
from datetime import date, datetime
from typing import Dict, List, Any, Optional
from src.engine.currency_normalizer import CurrencyNormalizer, MissingCurrencyConversionException
from src.engine.fte_normalizer import FTENormalizer
from src.engine.comparable_groups import ComparableGroupEngine


class ExceptionDetector:
    """Detects and isolates data violations, edge cases, and compliance anomalies."""

    def __init__(
        self,
        currency_normalizer: Optional[CurrencyNormalizer] = None,
        comparable_group_engine: Optional[ComparableGroupEngine] = None
    ):
        self.fx_normalizer = currency_normalizer or CurrencyNormalizer()
        self.group_engine = comparable_group_engine or ComparableGroupEngine()

    @staticmethod
    def check_expired_band_comparison(
        salary_effective_date: Any,
        band_start_date: Any,
        band_end_date: Optional[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Mandatory Edge Case 1: Salary compared against an expired compensation band.
        Validates: band_start_date <= salary_effective_date <= band_end_date.
        """
        if isinstance(salary_effective_date, str):
            salary_effective_date = datetime.strptime(salary_effective_date, "%Y-%m-%d").date()
        if isinstance(band_start_date, str):
            band_start_date = datetime.strptime(band_start_date, "%Y-%m-%d").date()
        if band_end_date is not None and isinstance(band_end_date, str):
            band_end_date = datetime.strptime(band_end_date, "%Y-%m-%d").date()

        if band_end_date and salary_effective_date > band_end_date:
            return {
                "issue_type": "EXPIRED_BAND_COMPARISON",
                "severity": "CRITICAL",
                "description": f"Salary effective date ({salary_effective_date}) is after band expiration date ({band_end_date}).",
                "detected_value": str(salary_effective_date),
                "expected_value": f"<= {band_end_date}",
                "recommendation": "Associate salary with active effective-dated compensation band for the corresponding period."
            }
        if salary_effective_date < band_start_date:
            return {
                "issue_type": "EXPIRED_BAND_COMPARISON",
                "severity": "CRITICAL",
                "description": f"Salary effective date ({salary_effective_date}) precedes band inception date ({band_start_date}).",
                "detected_value": str(salary_effective_date),
                "expected_value": f">= {band_start_date}",
                "recommendation": "Associate salary with contemporaneous historical compensation band."
            }
        return None

    @staticmethod
    def check_fte_ignored(
        recorded_normalized_salary: float,
        base_salary: float,
        fte: float,
        pay_frequency: str = "ANNUAL",
        fx_rate: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Mandatory Edge Case 2: FTE ignored during salary normalization.
        Detects if part-time salary was left unadjusted rather than scaled by 1/FTE.
        """
        if fte is None or fte <= 0 or fte > 1.0:
            return {
                "issue_type": "FTE_IGNORED_IN_NORMALIZATION",
                "severity": "CRITICAL",
                "description": f"Invalid FTE value: {fte}. Must be in (0.0, 1.0].",
                "detected_value": str(fte),
                "expected_value": "(0.0, 1.0]",
                "recommendation": "Correct employee FTE fraction in primary profile."
            }

        if abs(fte - 1.0) > 0.001:
            annual_base = FTENormalizer.annualize(base_salary, pay_frequency)
            expected_normalized = round((annual_base * fx_rate) / fte, 2)
            unadjusted_salary = round(annual_base * fx_rate, 2)

            # If recorded matches unadjusted rather than expected:
            if FTENormalizer.is_fte_ignored(recorded_normalized_salary, base_salary, fte, pay_frequency, fx_rate):
                return {
                    "issue_type": "FTE_IGNORED_IN_NORMALIZATION",
                    "severity": "CRITICAL",
                    "description": f"Part-time salary (FTE {fte}) was not normalized to full-time equivalent. Recorded: {recorded_normalized_salary}, Expected: {expected_normalized}.",
                    "detected_value": float(recorded_normalized_salary),
                    "expected_value": float(expected_normalized),
                    "recommendation": f"Re-normalize base salary by dividing by FTE ({fte})."
                }
        return None

    def check_currency_conversion(
        self,
        currency: str,
        effective_date: Any,
        reporting_currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """
        Mandatory Edge Case 3: Currency conversion missing.
        Verifies exchange rate presence in effective exchange rate table.
        """
        if currency == reporting_currency:
            return None

        if isinstance(effective_date, str):
            effective_date = datetime.strptime(effective_date, "%Y-%m-%d").date()

        try:
            rate = self.fx_normalizer.get_rate(currency, reporting_currency, effective_date)
            if rate <= 0:
                return {
                    "issue_type": "MISSING_CURRENCY_CONVERSION",
                    "severity": "CRITICAL",
                    "description": f"Invalid exchange rate ({rate}) for currency {currency} on {effective_date}.",
                    "detected_value": float(rate),
                    "expected_value": "> 0.0",
                    "recommendation": "Configure valid non-zero exchange rate in exchange_rates table."
                }
        except MissingCurrencyConversionException as e:
            return {
                "issue_type": "MISSING_CURRENCY_CONVERSION",
                "severity": "CRITICAL",
                "description": str(e),
                "detected_value": currency,
                "expected_value": f"Active rate for {currency}->{reporting_currency} on {effective_date}",
                "recommendation": f"Add effective-dated currency exchange rate for {currency} to {reporting_currency}."
            }
        return None

    @staticmethod
    def check_unapproved_adjustment_applied(
        salary_change_reason: str,
        proposal_status: Optional[str],
        has_approved_audit_event: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Mandatory Edge Case 4: Adjustment applied without approval.
        Enforces that equity/market salary changes require an APPROVED proposal and audit event.
        """
        equity_reasons = {"EQUITY_CORRECTION", "MARKET_ADJUSTMENT"}
        if salary_change_reason in equity_reasons:
            if proposal_status != "APPROVED" or not has_approved_audit_event:
                return {
                    "issue_type": "UNAPPROVED_ADJUSTMENT_APPLIED",
                    "severity": "CRITICAL",
                    "description": f"Salary reflects '{salary_change_reason}' but corresponding proposal status is '{proposal_status}' (audit event approved: {has_approved_audit_event}).",
                    "detected_value": f"status={proposal_status}, audit_approved={has_approved_audit_event}",
                    "expected_value": "status=APPROVED and audit_approved=True",
                    "recommendation": "Roll back unapproved salary record or execute formal approval workflow."
                }
        return None

    def check_incomparable_roles_grouped(
        self,
        role_a: str,
        role_b: str
    ) -> Optional[Dict[str, Any]]:
        """
        Mandatory Edge Case 5: Incomparable roles grouped without documented rationale.
        Verifies comparability via role bridge table.
        """
        if role_a == role_b:
            return None

        is_valid, reason = self.group_engine.validate_role_pair_comparability(role_a, role_b)
        if not is_valid:
            return {
                "issue_type": "INCOMPARABLE_ROLE_GROUPING",
                "severity": "HIGH",
                "description": f"Roles '{role_a}' and '{role_b}' grouped together without documented comparability rationale ({reason}).",
                "detected_value": f"{role_a} & {role_b}",
                "expected_value": "Approved comparability rationale in role_comparability_rationales",
                "recommendation": "Separate roles into distinct cohorts or submit formal comparability rationale to Compensation Committee."
            }
        return None
