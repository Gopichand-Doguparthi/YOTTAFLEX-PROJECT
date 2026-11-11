"""
Tests for Data Quality and Relational Validation Suite.
"""
from src.database.models import Employee, Level, Role, Location, CompensationBand
from src.validation.data_validator import DataValidator


def test_validation_passes_on_clean_data(db_session, sample_master_data):
    results = DataValidator.run_all_checks(db_session)
    assert results["pass_rate_pct"] == 100.0
    assert results["failed_checks"] == 0
    assert results["passed_checks"] == results["total_checks"]


def test_validation_detects_fte_violation(db_session, sample_master_data):
    from datetime import date
    # Invalidate employee FTE (1.5 > 1.0)
    invalid_emp = Employee(
        employee_id="EMP-FAIL01",
        first_name="Bad",
        last_name="FTE",
        email="bad.fte@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2024, 1, 1),
        fte=1.5
    )
    # Bypass check constraint in test setup to simulate dirty data in DB
    db_session.execute(
        Employee.__table__.insert().values(
            employee_id="EMP-FAIL01",
            first_name="Bad",
            last_name="FTE",
            email="bad.fte@company.org",
            department="Engineering",
            current_role_id="ROLE-SWE",
            current_level_id="LVL-L3",
            current_location_id="LOC-NYC",
            hire_date=date(2024, 1, 1),
            employment_type="FULL_TIME",
            fte=1.5,
            is_active=True,
            created_at=date(2024, 1, 1),
            updated_at=date(2024, 1, 1)
        )
    )
    db_session.flush()

    check = DataValidator.check_fte_ranges(db_session)
    assert check["passed"] is False
    assert check["violations_count"] > 0
