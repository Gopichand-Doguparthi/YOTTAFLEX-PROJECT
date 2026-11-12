"""
Regression tests for Stage 2 Audit Fixes:
1. Non-USD band currency conversion in /employees/{id} and /disparities.
2. Zero ground-truth leakage in /exceptions.
3. Approval RBAC and self-approval prevention in ProposalManager & API.
4. Enhanced DataValidator arithmetic reconciliation and duplicate detection.
"""
from datetime import date
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.employees import get_db
from src.database.models import (
    Location, Role, Level, CompensationBand, Employee, SalaryRecord,
    PerformanceEvidence, Tenure, ExchangeRate, GroundTruthRecord
)
from src.workflow.proposal_manager import ProposalManager, UnauthorizedApprovalException
from src.validation.data_validator import DataValidator


def test_non_usd_band_conversion_in_api(db_session, sample_master_data):
    """Verify INR employee benchmarked against INR band yields ~1.0 compa-ratio in API routes."""
    loc_blr = Location(
        location_id="LOC-BLR-TEST",
        location_name="Bangalore, India",
        country="IND",
        currency="INR",
        geo_tier="Tier-3",
        cost_of_living_index=0.35,
    )
    fx_inr = ExchangeRate(
        exchange_rate_id="FX-INR-USD-2026-TEST",
        from_currency="INR",
        to_currency="USD",
        rate=0.0115,
        effective_start_date=date(2026, 1, 1),
        effective_end_date=date(2026, 12, 31),
    )
    band_blr = CompensationBand(
        band_id="BAND-ROLE-SWE-LVL-L3-LOC-BLR-TEST-2026",
        role_id="ROLE-SWE",
        level_id="LVL-L3",
        location_id="LOC-BLR-TEST",
        currency="INR",
        min_salary=3600000.0,
        mid_salary=4400000.0,
        max_salary=5200000.0,
        effective_start_date=date(2026, 1, 1),
        effective_end_date=date(2026, 12, 31),
        status="ACTIVE",
    )
    emp = Employee(
        employee_id="EMP-888001",
        first_name="Aarav",
        last_name="Sharma",
        email="aarav.sharma@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-BLR-TEST",
        hire_date=date(2024, 1, 1),
        employment_type="FULL_TIME",
        fte=1.0,
        is_active=True,
    )
    # 4,400,000 INR * 0.0115 = 50,600 USD -> exact 1.00 compa-ratio
    sal = SalaryRecord(
        salary_id="SAL-EMP-888001-2026-01",
        employee_id="EMP-888001",
        base_salary=4400000.0,
        currency="INR",
        fte=1.0,
        pay_frequency="ANNUAL",
        normalized_salary=50600.0,
        normalized_currency="USD",
        effective_date=date(2026, 1, 1),
        change_reason="ANNUAL_MERIT",
    )
    perf = PerformanceEvidence(
        evidence_id="PERF-888001-2026",
        employee_id="EMP-888001",
        review_cycle="2026-ANNUAL",
        rating_score=4.5,
        rating_label="OUTSTANDING",
        effective_date=date(2026, 1, 1),
        reviewer_id=None,
    )
    tenure = Tenure(
        tenure_id="TEN-888001",
        employee_id="EMP-888001",
        company_start_date=date(2024, 1, 1),
        role_start_date=date(2024, 1, 1),
        years_of_experience_total=4.0,
        tenure_in_company_years=2.5,
        tenure_in_role_years=2.0,
    )
    db_session.add_all([loc_blr, fx_inr, band_blr, emp, sal, perf, tenure])
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        resp = client.get("/employees/EMP-888001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compa_ratio"] == pytest.approx(1.0, abs=0.01)
        assert data["within_band_position"] == pytest.approx(0.5, abs=0.01)

        disp_resp = client.get("/disparities?only_unexplained=false&location_id=LOC-BLR-TEST")
        assert disp_resp.status_code == 200
        disp_rows = disp_resp.json()
        assert len(disp_rows) == 1
        assert disp_rows[0]["compa_ratio"] == pytest.approx(1.0, abs=0.01)
        assert disp_rows[0]["is_disparity"] is False
    finally:
        app.dependency_overrides.clear()


def test_exceptions_endpoint_does_not_leak_ground_truth(db_session, sample_master_data):
    """Adding a GroundTruthRecord alone must NOT appear in /exceptions output."""
    gt_only = GroundTruthRecord(
        gt_id="GT-LEAK-TEST",
        record_type="COMPARABLE_GROUP",
        record_id="GRP-ROLE-PM-ROLE-REC",
        issue_type="INCOMPARABLE_ROLE_GROUPING",
        expected_detection="EXCEPTION_FLAGGED",
        explanation="Ground truth only record.",
    )
    db_session.add(gt_only)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        resp = client.get("/exceptions?issue_type=INCOMPARABLE_ROLE_GROUPING")
        assert resp.status_code == 200
        record_ids = {e["record_id"] for e in resp.json()["exceptions"]}
        assert "GRP-ROLE-PM-ROLE-REC" not in record_ids
    finally:
        app.dependency_overrides.clear()


def test_approval_rbac_and_self_approval_blocked(db_session, sample_master_data):
    """Unauthorized roles and self-approval must be rejected with UnauthorizedApprovalException / HTTP 403."""
    emp = Employee(
        employee_id="EMP-888002",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2024, 1, 1),
        fte=1.0,
    )
    db_session.add(emp)
    db_session.flush()

    prop = ProposalManager.create_proposal(
        session=db_session,
        employee_id="EMP-888002",
        current_salary=130000.0,
        proposed_salary=145000.0,
        reason_code="INTERNAL_EQUITY",
        justification_notes="Peer equity.",
        evidence_summary={"rating": 4.2},
        related_disparity_findings={"deviation": -16.0},
        proposed_effective_date=date(2026, 5, 1),
        created_by="hr.creator@company.org",
        custom_id="ADJ-2026-888002",
    )
    ProposalManager.submit_for_review(db_session, prop.proposal_id, submitted_by="hr.creator@company.org")

    with pytest.raises(UnauthorizedApprovalException):
        ProposalManager.approve_proposal(
            db_session, prop.proposal_id, reviewed_by="other.emp@company.org", actor_role="EMPLOYEE"
        )

    with pytest.raises(UnauthorizedApprovalException):
        ProposalManager.approve_proposal(
            db_session, prop.proposal_id, reviewed_by="hr.creator@company.org", actor_role="HR_PARTNER"
        )

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)
        resp_403 = client.post(
            f"/proposals/{prop.proposal_id}/review",
            json={"reviewed_by": "hr.creator@company.org", "decision": "APPROVED", "actor_role": "MANAGER"},
        )
        assert resp_403.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_validator_detects_arithmetic_and_duplicate_violations(db_session, sample_master_data):
    """DataValidator must catch normalized_salary arithmetic mismatches and duplicate effective dates."""
    emp = Employee(
        employee_id="EMP-888003",
        first_name="Liam",
        last_name="Ng",
        email="liam.ng@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2024, 1, 1),
        fte=0.5,
    )
    sal1 = SalaryRecord(
        salary_id="SAL-EMP-888003-2026-01",
        employee_id="EMP-888003",
        base_salary=60000.0,
        currency="USD",
        fte=0.5,
        pay_frequency="ANNUAL",
        normalized_salary=60000.0,  # Wrong! Should be 120000.0
        normalized_currency="USD",
        effective_date=date(2026, 1, 1),
        change_reason="HIRE",
    )
    sal2 = SalaryRecord(
        salary_id="SAL-EMP-888003-2026-02",
        employee_id="EMP-888003",
        base_salary=60000.0,
        currency="USD",
        fte=0.5,
        pay_frequency="ANNUAL",
        normalized_salary=120000.0,
        normalized_currency="USD",
        effective_date=date(2026, 1, 1),  # Duplicate effective_date for same employee
        change_reason="ANNUAL_MERIT",
    )
    db_session.add_all([emp, sal1, sal2])
    db_session.flush()

    arith = DataValidator.check_salary_normalization_arithmetic(db_session)
    assert arith["passed"] is False
    assert arith["violations_count"] >= 1

    dups = DataValidator.check_duplicate_records(db_session)
    assert dups["passed"] is False
    assert dups["violations_count"] >= 1
