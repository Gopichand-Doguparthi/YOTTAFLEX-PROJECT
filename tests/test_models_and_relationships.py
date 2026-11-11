"""
Tests for SQLAlchemy Relational Models and Schema Constraints.
"""
from datetime import date
from src.database.models import (
    Employee, Role, Level, Location, CompensationBand,
    SalaryRecord, PerformanceEvidence, Tenure, Promotion,
    AdjustmentProposal
)


def test_core_entities_and_relationships(db_session, sample_master_data):
    # 1. Create employee
    emp = Employee(
        employee_id="EMP-REL001",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe.rel@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2023, 1, 1),
        employment_type="FULL_TIME",
        fte=1.0,
        is_active=True
    )
    db_session.add(emp)
    db_session.flush()

    # 2. Add tenure
    tenure = Tenure(
        tenure_id="TEN-EMP-REL001",
        employee_id=emp.employee_id,
        company_start_date=date(2023, 1, 1),
        role_start_date=date(2023, 1, 1),
        years_of_experience_total=5.0,
        tenure_in_company_years=3.0,
        tenure_in_role_years=3.0
    )
    db_session.add(tenure)

    # 3. Add salary record
    sal = SalaryRecord(
        salary_id="SAL-EMP-REL001-2026-01",
        employee_id=emp.employee_id,
        base_salary=145000.0,
        currency="USD",
        fte=1.0,
        pay_frequency="ANNUAL",
        normalized_salary=145000.0,
        normalized_currency="USD",
        effective_date=date(2026, 1, 1),
        change_reason="ANNUAL_MERIT"
    )
    db_session.add(sal)

    # 4. Add performance evaluation
    perf = PerformanceEvidence(
        evidence_id="PERF-EMP-REL001-2025-H2",
        employee_id=emp.employee_id,
        review_cycle="2025-H2",
        rating_score=4.2,
        rating_label="EXCEEDS_EXPECTATIONS",
        documented_skills_score=85.0,
        critical_initiative_count=2,
        effective_date=date(2025, 12, 31)
    )
    db_session.add(perf)

    db_session.flush()

    # Verify relationships via ORM
    loaded_emp = db_session.query(Employee).filter_by(employee_id="EMP-REL001").first()
    assert loaded_emp is not None
    assert loaded_emp.role.role_title == "Software Engineer"
    assert loaded_emp.level.level_name == "Senior"
    assert loaded_emp.location.location_name == "New York, USA"
    assert len(loaded_emp.salary_records) == 1
    assert loaded_emp.salary_records[0].base_salary == 145000.0
    assert len(loaded_emp.performance_records) == 1
    assert loaded_emp.performance_records[0].rating_score == 4.2
    assert loaded_emp.tenure.years_of_experience_total == 5.0
