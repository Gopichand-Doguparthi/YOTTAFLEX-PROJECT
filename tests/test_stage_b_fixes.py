"""
Stage B Regression & Integration Tests:
1. Evaluator VALID_BASELINE false-positive & TP/FP/TN/FN accounting.
2. Alembic 002_add_review_cases fresh-DB upgrade/downgrade/upgrade.
3. Synthetic generator benchmark_band_id population & expired-band preservation.
4. ReviewCase REST API CRUD, transitions, duplicates, and audit logging.
5. JWT Bearer authentication & server-side RBAC enforcement.
"""
import os
import tempfile
from datetime import date
import pytest
from fastapi.testclient import TestClient
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

from src.api.main import app
from src.api.auth import create_access_token
from src.api.routes.employees import get_db
from src.database.models import (
    Employee, SalaryRecord, PerformanceEvidence, Tenure,
    CompensationBand, GroundTruthRecord, ReviewCase, ApprovalEvent
)
from src.evaluation.evaluator import EvaluationEngine
from src.generator.synthetic_generator import SyntheticDataGenerator


def test_evaluator_counts_baseline_false_positives_and_all_outcomes(db_session, sample_master_data):
    """
    Tests all 6 required evaluation outcomes:
    1. VALID_BASELINE not detected -> TN
    2. VALID_BASELINE incorrectly flagged by DisparityDetector -> FP
    3. Genuine unexplained disparity detected -> TP
    4. Genuine unexplained disparity missed -> FN
    5. Operational exception (Expired Band) detected -> TP
    6. Operational exception (Expired Band) missed -> FN
    """
    # Create 4-person cohort in ROLE-SWE / LVL-L3 / LOC-NYC (Band mid=150,000)
    # E1: VALID_BASELINE normal (150k) -> TN
    # E2: VALID_BASELINE flagged as FP (110k, rating 4.8, tenure 3yr -> flagged by detector, labeled VALID_BASELINE) -> FP
    # E3: UNEXPLAINED_DISPARITY_LOW detected (108k, rating 4.8, tenure 3yr) -> TP
    # E4: UNEXPLAINED_DISPARITY_LOW missed (145k, rating 4.8, tenure 3yr -> within band so missed) -> FN
    cohort = [
        ("EMP-EV01", 150000.0, False, "VALID_BASELINE"),
        ("EMP-EV02", 110000.0, False, "VALID_BASELINE"),
        ("EMP-EV03", 108000.0, True, "UNEXPLAINED_DISPARITY_LOW"),
        ("EMP-EV04", 145000.0, True, "UNEXPLAINED_DISPARITY_LOW"),
    ]
    for eid, sal_amt, is_anom, issue in cohort:
        db_session.add(Employee(
            employee_id=eid, first_name="Test", last_name=eid, email=f"{eid.lower()}@test.org",
            department="Engineering", current_role_id="ROLE-SWE", current_level_id="LVL-L3",
            current_location_id="LOC-NYC", hire_date=date(2022, 1, 1), fte=1.0, is_active=True
        ))
        db_session.add(SalaryRecord(
            salary_id=f"SAL-{eid}-2026-01", employee_id=eid, base_salary=sal_amt, currency="USD",
            fte=1.0, pay_frequency="ANNUAL", normalized_salary=sal_amt, normalized_currency="USD",
            effective_date=date(2026, 1, 1), change_reason="ANNUAL_MERIT",
            benchmark_band_id="BAND-ROLE-SWE-LVL-L3-LOC-NYC-2026"
        ))
        db_session.add(PerformanceEvidence(
            evidence_id=f"PERF-{eid}-2026", employee_id=eid, review_cycle="2026-ANNUAL",
            rating_score=4.8, rating_label="OUTSTANDING", effective_date=date(2026, 1, 1)
        ))
        db_session.add(Tenure(
            tenure_id=f"TEN-{eid}", employee_id=eid, company_start_date=date(2022, 1, 1),
            role_start_date=date(2022, 1, 1), years_of_experience_total=5.0,
            tenure_in_company_years=3.0, tenure_in_role_years=3.0
        ))
        db_session.add(GroundTruthRecord(
            ground_truth_id=f"GT-{eid}", record_type="EMPLOYEE", record_id=eid,
            issue_type=issue, is_anomaly=is_anom,
            expected_detection="DISPARITY_DETECTED" if is_anom else "NONE",
            root_cause_explanation="Evaluation test case."
        ))

    # 5. Operational exception detected: E1's 2024 expired band compared in 2026 -> TP
    db_session.add(CompensationBand(
        band_id="BAND-ROLE-SWE-LVL-L3-LOC-NYC-2024", role_id="ROLE-SWE", level_id="LVL-L3",
        location_id="LOC-NYC", currency="USD", min_salary=100000.0, mid_salary=125000.0,
        max_salary=150000.0, effective_start_date=date(2024, 1, 1), effective_end_date=date(2024, 12, 31),
        status="EXPIRED"
    ))
    db_session.add(SalaryRecord(
        salary_id="SAL-EMP-EV05-2026-01", employee_id="EMP-EV01", base_salary=150000.0, currency="USD",
        fte=1.0, pay_frequency="ANNUAL", normalized_salary=150000.0, normalized_currency="USD",
        effective_date=date(2026, 2, 1), change_reason="ANNUAL_MERIT",
        benchmark_band_id="BAND-ROLE-SWE-LVL-L3-LOC-NYC-2024"
    ))
    db_session.add(GroundTruthRecord(
        ground_truth_id="GT-EXC-TP", record_type="SALARY_RECORD", record_id="SAL-EMP-EV05-2026-01",
        issue_type="EXPIRED_BAND_COMPARISON", is_anomaly=True,
        expected_detection="EXCEPTION_FLAGGED", root_cause_explanation="Detected expired band."
    ))

    # 6. Operational exception missed: GT says EXPIRED_BAND_COMPARISON on active 2026 band -> FN
    db_session.add(GroundTruthRecord(
        ground_truth_id="GT-EXC-FN", record_type="SALARY_RECORD", record_id="SAL-EMP-EV01-2026-01",
        issue_type="EXPIRED_BAND_COMPARISON", is_anomaly=True,
        expected_detection="EXCEPTION_FLAGGED", root_cause_explanation="Missed exception test."
    ))
    db_session.flush()

    res = EvaluationEngine.evaluate(db_session)
    m = res["overall_metrics"]
    assert m["true_negatives"] == 1    # EMP-EV01
    assert m["false_positives"] == 1   # EMP-EV02 (VALID_BASELINE flagged!)
    assert m["true_positives"] == 2    # EMP-EV03 + SAL-EMP-EV05-2026-01
    assert m["false_negatives"] == 2   # EMP-EV04 + GT-EXC-FN


def test_alembic_fresh_database_upgrade_and_downgrade(tmp_path):
    """Verify Alembic migrations 001 -> 002 -> 001 -> 002 on a fresh temporary SQLite DB."""
    db_file = tmp_path / "fresh_alembic.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")
    eng = create_engine(db_url)
    insp = inspect(eng)
    assert insp.has_table("review_cases")
    assert insp.has_table("employees")
    eng.dispose()

    command.downgrade(cfg, "001_initial_schema")
    eng2 = create_engine(db_url)
    assert not inspect(eng2).has_table("review_cases")
    assert inspect(eng2).has_table("employees")
    eng2.dispose()

    command.upgrade(cfg, "head")
    eng3 = create_engine(db_url)
    assert inspect(eng3).has_table("review_cases")
    eng3.dispose()


def test_synthetic_generator_populates_benchmark_band_id_and_preserves_expired():
    """Baseline salary records get matching-year bands; Edge Case 1 gets expired 2024 band on 2026 salary."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    data = gen.generate_all()
    bands_by_id = {b["band_id"]: b for b in data["compensation_bands"]}
    gt_expired = {g["record_id"] for g in data["ground_truth_records"] if g["issue_type"] == "EXPIRED_BAND_COMPARISON"}
    gt_unapproved = {g["record_id"] for g in data["ground_truth_records"] if g["issue_type"] == "UNAPPROVED_ADJUSTMENT_APPLIED"}

    assert len(gt_expired) > 0
    for sal in data["salary_records"]:
        sid = sal["salary_id"]
        if sid in gt_unapproved:
            assert sal.get("benchmark_band_id") is None
        elif sid in gt_expired:
            b = bands_by_id[sal["benchmark_band_id"]]
            assert sal["effective_date"].startswith("2026")
            assert b["status"] == "EXPIRED"
        else:
            b = bands_by_id.get(sal.get("benchmark_band_id"))
            assert b is not None
            eff_yr = sal["effective_date"][:4]
            assert b["band_id"].endswith(f"-{eff_yr}")


def test_review_case_rest_api_and_auth_enforcement(db_session, sample_master_data, monkeypatch):
    """Verify ReviewCase GET/POST/PATCH, state transitions, audit events, and JWT RBAC."""
    monkeypatch.setenv("DEV_AUTH_PASSWORD", "test-dev-pw")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")

    emp = Employee(
        employee_id="EMP-RC001", first_name="Nina", last_name="Patel", email="nina.patel@test.org",
        department="Engineering", current_role_id="ROLE-SWE", current_level_id="LVL-L3",
        current_location_id="LOC-NYC", hire_date=date(2023, 1, 1), fte=1.0
    )
    db_session.add(emp)
    db_session.flush()

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        client = TestClient(app)

        # Token endpoint checks
        assert client.post("/auth/token", json={"email": "hr.partner@company.org", "password": "wrong"}).status_code == 401
        tok_hr = client.post("/auth/token", json={"email": "hr.partner@company.org", "password": "test-dev-pw"})
        assert tok_hr.status_code == 200
        hr_headers = {"Authorization": f"Bearer {tok_hr.json()['access_token']}"}
        emp_headers = {"Authorization": f"Bearer {create_access_token('emp@test.org', 'EMPLOYEE')}"}

        # Unauthenticated -> 401; EMPLOYEE role -> 403
        assert client.get("/review-cases").status_code == 401
        assert client.post("/review-cases", json={"employee_id": "EMP-RC001"}).status_code == 401
        assert client.post("/review-cases", json={"employee_id": "EMP-RC001"}, headers=emp_headers).status_code == 403

        # Create -> 201
        r_create = client.post("/review-cases", json={"employee_id": "EMP-RC001", "comments": "Initial flag."}, headers=hr_headers)
        assert r_create.status_code == 201
        case_id = r_create.json()["case_id"]
        assert r_create.json()["status"] == "OPEN"

        # Duplicate -> 409; missing employee -> 404
        assert client.post("/review-cases", json={"employee_id": "EMP-RC001"}, headers=hr_headers).status_code == 409
        assert client.post("/review-cases", json={"employee_id": "EMP-NONE"}, headers=hr_headers).status_code == 404

        # List & Get
        assert client.get("/review-cases", headers=hr_headers).status_code == 200
        assert client.get(f"/review-cases/{case_id}", headers=hr_headers).status_code == 200
        assert client.get("/review-cases/CASE-NONE", headers=hr_headers).status_code == 404

        # Invalid transition OPEN -> REOPENED -> 400
        assert client.patch(f"/review-cases/{case_id}", json={"status": "REOPENED"}, headers=hr_headers).status_code == 400

        # Valid transitions: OPEN -> IN_REVIEW -> RESOLVED -> REOPENED
        assert client.patch(f"/review-cases/{case_id}", json={"status": "IN_REVIEW"}, headers=hr_headers).status_code == 200
        assert client.patch(f"/review-cases/{case_id}", json={"status": "RESOLVED", "comments": "Reviewed & cleared."}, headers=hr_headers).status_code == 200
        r_reopen = client.patch(f"/review-cases/{case_id}", json={"status": "REOPENED"}, headers=hr_headers)
        assert r_reopen.status_code == 200
        assert r_reopen.json()["status"] == "REOPENED"

        # Audit events logged
        events = db_session.query(ApprovalEvent).filter_by(entity_name="ReviewCase", entity_id=case_id).all()
        assert len(events) >= 4
    finally:
        app.dependency_overrides.clear()
