"""
Tests for Disparity Detection Logic and Rule Engine.
"""
import pytest
from src.engine.disparity_detector import DisparityDetector


def test_unexplained_disparity_flagged():
    detector = DisparityDetector()
    # High performer (rating 4.5), 3 years tenure, earning 100k vs cohort median 150k (-33% deviation, CR 0.67)
    res = detector.evaluate_employee(
        employee_id="EMP-000001",
        normalized_salary=100000.0,
        band_min=120000.0,
        band_mid=150000.0,
        band_max=180000.0,
        cohort_median_salary=150000.0,
        cohort_size=10,
        performance_rating=4.5,
        tenure_in_role_years=2.0,
        tenure_in_company_years=3.0,
        has_pending_adjustment=False
    )
    assert res.is_disparity is True
    assert res.status == "UNEXPLAINED_DISPARITY"
    assert res.compa_ratio == 0.6667
    assert res.deviation_from_cohort_median_pct == -33.33
    assert "unexplained by strong performance" in res.primary_reason


def test_explained_variation_low_tenure():
    detector = DisparityDetector()
    # New hire with 0.4 years company tenure
    res = detector.evaluate_employee(
        employee_id="EMP-000002",
        normalized_salary=120000.0,
        band_min=120000.0,
        band_mid=150000.0,
        band_max=180000.0,
        cohort_median_salary=150000.0,
        cohort_size=8,
        performance_rating=3.0,
        tenure_in_company_years=0.4
    )
    assert res.is_disparity is False
    assert res.status == "EXPLAINED_VARIATION"
    assert "recent hire" in res.primary_reason


def test_manual_review_required_for_extreme_outlier():
    detector = DisparityDetector()
    # Extreme positive deviation (+35%) with low performance rating (2.2)
    res = detector.evaluate_employee(
        employee_id="EMP-000003",
        normalized_salary=202500.0,
        band_min=120000.0,
        band_mid=150000.0,
        band_max=180000.0,
        cohort_median_salary=150000.0,
        cohort_size=12,
        performance_rating=2.2,
        tenure_in_company_years=2.0
    )
    assert res.is_disparity is False
    assert res.status == "MANUAL_REVIEW_REQUIRED"
    assert "High positive deviation" in res.primary_reason


def test_insufficient_evidence_small_cohort():
    detector = DisparityDetector()
    # Cohort size of 2 (< min_cohort_size of 3)
    res = detector.evaluate_employee(
        employee_id="EMP-000004",
        normalized_salary=110000.0,
        band_min=100000.0,
        band_mid=130000.0,
        band_max=160000.0,
        cohort_median_salary=130000.0,
        cohort_size=2,
        performance_rating=4.0
    )
    assert res.status == "INSUFFICIENT_EVIDENCE"
    assert res.is_disparity is False


def test_invalid_comparison_with_exception():
    detector = DisparityDetector()
    res = detector.evaluate_employee(
        employee_id="EMP-000005",
        normalized_salary=100000.0,
        band_min=100000.0,
        band_mid=120000.0,
        band_max=140000.0,
        cohort_median_salary=120000.0,
        cohort_size=5,
        has_active_exception=True,
        exception_details="Expired compensation band"
    )
    assert res.status == "INVALID_COMPARISON"
    assert res.is_disparity is False
