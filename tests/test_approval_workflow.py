"""
Tests for Adjustment Proposal Lifecycle and Approval Transitions.
"""
import pytest
from datetime import date
from src.database.models import Employee, SalaryRecord, AdjustmentProposal, ApprovalEvent
from src.workflow.proposal_manager import ProposalManager, InvalidLifecycleTransitionException


def test_proposal_lifecycle_flow(db_session, sample_master_data):
    # Setup test employee
    emp = Employee(
        employee_id="EMP-999001",
        first_name="Alice",
        last_name="Tester",
        email="alice.tester@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2023, 1, 1),
        employment_type="FULL_TIME",
        fte=1.0,
        is_active=True
    )
    sal = SalaryRecord(
        salary_id="SAL-EMP-999001-2026-01",
        employee_id=emp.employee_id,
        base_salary=130000.0,
        currency="USD",
        fte=1.0,
        pay_frequency="ANNUAL",
        normalized_salary=130000.0,
        normalized_currency="USD",
        effective_date=date(2026, 1, 1),
        change_reason="HIRE"
    )
    db_session.add_all([emp, sal])
    db_session.flush()

    # Step 1: Create Proposal (DRAFT)
    prop = ProposalManager.create_proposal(
        session=db_session,
        employee_id=emp.employee_id,
        current_salary=130000.0,
        proposed_salary=150000.0,
        reason_code="INTERNAL_EQUITY",
        justification_notes="Remediation for equity disparity.",
        evidence_summary={"rating": 4.5},
        related_disparity_findings={"deviation": -18.0},
        proposed_effective_date=date(2026, 4, 1),
        created_by="hr.partner@company.org",
        custom_id="ADJ-2026-999001"
    )
    assert prop.approval_status == "DRAFT"
    assert prop.adjustment_amount == 20000.0
    assert prop.adjustment_percentage == round((20000.0 / 130000.0) * 100, 2)

    # Step 2: Submit for review (PENDING_REVIEW)
    ProposalManager.submit_for_review(
        session=db_session,
        proposal_id=prop.proposal_id,
        submitted_by="hr.partner@company.org"
    )
    assert prop.approval_status == "PENDING_REVIEW"

    # Step 3: Approve proposal (APPROVED)
    ProposalManager.approve_proposal(
        session=db_session,
        proposal_id=prop.proposal_id,
        reviewed_by="manager.lead@company.org",
        review_notes="Approved parity correction.",
        apply_salary_update=True
    )
    assert prop.approval_status == "APPROVED"
    assert prop.reviewed_by == "manager.lead@company.org"

    # Verify new SalaryRecord created with EQUITY_CORRECTION
    updated_sal = db_session.query(SalaryRecord).filter(
        SalaryRecord.employee_id == emp.employee_id,
        SalaryRecord.change_reason == "EQUITY_CORRECTION"
    ).first()
    assert updated_sal is not None
    assert updated_sal.base_salary == 150000.0
    assert updated_sal.normalized_salary == 150000.0


def test_invalid_lifecycle_transition_raises_error(db_session, sample_master_data):
    emp = Employee(
        employee_id="EMP-999002",
        first_name="Bob",
        last_name="Tester",
        email="bob.tester@company.org",
        department="Engineering",
        current_role_id="ROLE-SWE",
        current_level_id="LVL-L3",
        current_location_id="LOC-NYC",
        hire_date=date(2023, 1, 1),
        fte=1.0
    )
    db_session.add(emp)
    db_session.flush()

    prop = ProposalManager.create_proposal(
        session=db_session,
        employee_id=emp.employee_id,
        current_salary=120000.0,
        proposed_salary=140000.0,
        reason_code="MARKET_PARITY",
        justification_notes="Market parity.",
        evidence_summary={},
        related_disparity_findings={},
        proposed_effective_date=date(2026, 4, 1),
        created_by="hr.partner@company.org",
        custom_id="ADJ-2026-999002"
    )

    # Attempting to directly approve a DRAFT without submitting raises error
    with pytest.raises(InvalidLifecycleTransitionException):
        ProposalManager.approve_proposal(
            session=db_session,
            proposal_id=prop.proposal_id,
            reviewed_by="manager.lead@company.org"
        )
