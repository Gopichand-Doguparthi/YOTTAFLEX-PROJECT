"""
Comprehensive Test Suite for the Five Mandatory Edge Cases.
Validates:
1. Salary compared against an expired compensation band.
2. FTE ignored during salary normalization.
3. Currency conversion missing.
4. Adjustment applied without approval.
5. Incomparable roles grouped without documented rationale.
"""
import pytest
from datetime import date
from src.engine.currency_normalizer import CurrencyNormalizer, MissingCurrencyConversionException
from src.engine.fte_normalizer import FTENormalizer
from src.engine.comparable_groups import ComparableGroupEngine
from src.engine.exception_detector import ExceptionDetector


# ---------------------------------------------------------------------------
# Mandatory Edge Case 1: Salary compared against expired compensation band
# ---------------------------------------------------------------------------
def test_edge_case_1_salary_compared_to_expired_band():
    detector = ExceptionDetector()

    # Valid scenario: Salary effective in 2025 within 2025 band window
    valid_exc = detector.check_expired_band_comparison(
        salary_effective_date=date(2025, 6, 1),
        band_start_date=date(2025, 1, 1),
        band_end_date=date(2025, 12, 31)
    )
    assert valid_exc is None

    # Anomaly scenario: 2026 salary compared against 2024 expired band
    expired_exc = detector.check_expired_band_comparison(
        salary_effective_date=date(2026, 1, 1),
        band_start_date=date(2024, 1, 1),
        band_end_date=date(2024, 12, 31)
    )
    assert expired_exc is not None
    assert expired_exc["issue_type"] == "EXPIRED_BAND_COMPARISON"
    assert expired_exc["severity"] == "CRITICAL"
    assert "after band expiration date" in expired_exc["description"]


# ---------------------------------------------------------------------------
# Mandatory Edge Case 2: FTE ignored during salary normalization
# ---------------------------------------------------------------------------
def test_edge_case_2_fte_ignored_in_normalization():
    detector = ExceptionDetector()

    # Part-time employee with FTE = 0.5 earning 50,000 USD base
    # If correctly normalized: 50,000 / 0.5 = 100,000 USD
    valid_exc = detector.check_fte_ignored(
        recorded_normalized_salary=100000.0,
        base_salary=50000.0,
        fte=0.5,
        pay_frequency="ANNUAL",
        fx_rate=1.0
    )
    assert valid_exc is None

    # Anomaly scenario: recorded_normalized_salary left as raw 50,000 USD (FTE ignored)
    ignored_exc = detector.check_fte_ignored(
        recorded_normalized_salary=50000.0,
        base_salary=50000.0,
        fte=0.5,
        pay_frequency="ANNUAL",
        fx_rate=1.0
    )
    assert ignored_exc is not None
    assert ignored_exc["issue_type"] == "FTE_IGNORED_IN_NORMALIZATION"
    assert ignored_exc["severity"] == "CRITICAL"
    assert ignored_exc["detected_value"] == 50000.0
    assert ignored_exc["expected_value"] == 100000.0


# ---------------------------------------------------------------------------
# Mandatory Edge Case 3: Currency conversion missing
# ---------------------------------------------------------------------------
def test_edge_case_3_missing_currency_conversion():
    rates = [
        {"from_currency": "EUR", "to_currency": "USD", "rate": 1.10, "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"}
    ]
    normalizer = CurrencyNormalizer(rates=rates)
    detector = ExceptionDetector(currency_normalizer=normalizer)

    # Valid scenario: EUR rate is registered and effective
    valid_exc = detector.check_currency_conversion(
        currency="EUR",
        effective_date=date(2026, 6, 1)
    )
    assert valid_exc is None

    # Reporting currency (USD) needs no conversion
    usd_exc = detector.check_currency_conversion(
        currency="USD",
        effective_date=date(2026, 6, 1)
    )
    assert usd_exc is None

    # Anomaly scenario: Currency JPY missing exchange rate
    missing_exc = detector.check_currency_conversion(
        currency="JPY",
        effective_date=date(2026, 6, 1)
    )
    assert missing_exc is not None
    assert missing_exc["issue_type"] == "MISSING_CURRENCY_CONVERSION"
    assert missing_exc["severity"] == "CRITICAL"
    assert "JPY" in missing_exc["description"]


# ---------------------------------------------------------------------------
# Mandatory Edge Case 4: Adjustment applied without approval
# ---------------------------------------------------------------------------
def test_edge_case_4_unapproved_adjustment_applied():
    detector = ExceptionDetector()

    # Valid scenario: Salary reflects EQUITY_CORRECTION with APPROVED proposal and audit event
    valid_exc = detector.check_unapproved_adjustment_applied(
        salary_change_reason="EQUITY_CORRECTION",
        proposal_status="APPROVED",
        has_approved_audit_event=True
    )
    assert valid_exc is None

    # Anomaly scenario A: Proposal was REJECTED but salary was changed anyway
    rejected_exc = detector.check_unapproved_adjustment_applied(
        salary_change_reason="EQUITY_CORRECTION",
        proposal_status="REJECTED",
        has_approved_audit_event=False
    )
    assert rejected_exc is not None
    assert rejected_exc["issue_type"] == "UNAPPROVED_ADJUSTMENT_APPLIED"
    assert rejected_exc["severity"] == "CRITICAL"

    # Anomaly scenario B: Proposal marked APPROVED in DB but has no immutable approval audit event
    tampered_exc = detector.check_unapproved_adjustment_applied(
        salary_change_reason="EQUITY_CORRECTION",
        proposal_status="APPROVED",
        has_approved_audit_event=False
    )
    assert tampered_exc is not None
    assert tampered_exc["issue_type"] == "UNAPPROVED_ADJUSTMENT_APPLIED"


# ---------------------------------------------------------------------------
# Mandatory Edge Case 5: Incomparable roles grouped without rationale
# ---------------------------------------------------------------------------
def test_edge_case_5_incomparable_roles_grouped():
    rationales = [
        {
            "role_id_a": "ROLE-SWE",
            "role_id_b": "ROLE-FSE",
            "is_comparable": True,
            "documented_rationale": "Equivalent core software engineering competencies."
        }
    ]
    group_engine = ComparableGroupEngine(rationales=rationales)
    detector = ExceptionDetector(comparable_group_engine=group_engine)

    # Valid scenario: Comparing Software Engineer with Full Stack Engineer (Approved rationale)
    valid_exc = detector.check_incomparable_roles_grouped("ROLE-SWE", "ROLE-FSE")
    assert valid_exc is None

    # Anomaly scenario: Comparing Software Engineer with Facilities Coordinator (No rationale)
    incomparable_exc = detector.check_incomparable_roles_grouped("ROLE-SWE", "ROLE-FAC")
    assert incomparable_exc is not None
    assert incomparable_exc["issue_type"] == "INCOMPARABLE_ROLE_GROUPING"
    assert incomparable_exc["severity"] == "HIGH"
    assert "No documented comparability rationale" in incomparable_exc["description"]
