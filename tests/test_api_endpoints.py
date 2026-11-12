"""
Tests for FastAPI REST Endpoints.
"""
from datetime import date


def test_api_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_analytics_summary(client, sample_master_data):
    res = client.get("/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_employees" in data
    assert "total_compensation_bands" in data


def test_api_bands_list(client, sample_master_data):
    res = client.get("/bands?role_id=ROLE-SWE")
    assert res.status_code == 200
    bands = res.json()
    assert len(bands) >= 1
    assert bands[0]["role_id"] == "ROLE-SWE"


def test_api_validation_report(client, sample_master_data):
    res = client.get("/validation/integrity")
    assert res.status_code == 200
    data = res.json()
    assert data["pass_rate_pct"] == 100.0
    assert data["failed_checks"] == 0


def test_api_proposal_creation_and_review(client, sample_master_data, db_session):
    from src.database.models import Employee
    emp = Employee(
        employee_id="EMP-API001",
        first_name="David",
        last_name="API",
        email="david.api@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2023, 1, 1),
        fte=1.0
    )
    db_session.add(emp)
    db_session.flush()

    from src.api.auth import create_access_token
    hr_headers = {"Authorization": f"Bearer {create_access_token('hr.lead@company.org', 'HR_PARTNER')}"}
    mgr_headers = {"Authorization": f"Bearer {create_access_token('director@company.org', 'MANAGER')}"}

    # Create proposal
    payload = {
        "employee_id": "EMP-API001",
        "proposed_salary": 155000.0,
        "reason_code": "INTERNAL_EQUITY",
        "justification_notes": "Parity fix via API.",
        "proposed_effective_date": "2026-04-01",
        "created_by": "hr.lead@company.org"
    }
    create_res = client.post("/proposals", json=payload, headers=hr_headers)
    assert create_res.status_code == 200
    prop_data = create_res.json()
    assert prop_data["approval_status"] == "DRAFT"
    proposal_id = prop_data["proposal_id"]

    # Submit for review
    sub_res = client.post(f"/proposals/{proposal_id}/submit", headers=hr_headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["approval_status"] == "PENDING_REVIEW"

    # Review (Approve)
    rev_payload = {
        "reviewed_by": "director@company.org",
        "decision": "APPROVED",
        "review_notes": "Approved."
    }
    rev_res = client.post(f"/proposals/{proposal_id}/review", json=rev_payload, headers=mgr_headers)
    assert rev_res.status_code == 200
    assert rev_res.json()["approval_status"] == "APPROVED"
