"""
Adjustment Proposal Lifecycle and Remediation Workflow Manager.
Enforces finite-state transitions: DRAFT -> PENDING_REVIEW -> APPROVED / REJECTED.
Ensures deterministic IDs (ADJ-2026-000001) and append-only audit tracking.
"""
from datetime import datetime, date
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from src.database.models import AdjustmentProposal, Employee, SalaryRecord
from src.workflow.audit_logger import AuditLogger


class InvalidLifecycleTransitionException(Exception):
    """Raised when an illegal status change is attempted on a proposal."""
    pass


class ProposalManager:
    """Manages creation, review, approval, and application of salary adjustment proposals."""

    _proposal_counter = 0

    @classmethod
    def generate_proposal_id(cls, year: int = 2026) -> str:
        """Generates deterministic proposal ID matching ADJ-2026-000001."""
        cls._proposal_counter += 1
        return f"ADJ-{year}-{cls._proposal_counter:06d}"

    @classmethod
    def set_counter(cls, value: int):
        """Sets the proposal sequence counter."""
        cls._proposal_counter = value

    @classmethod
    def create_proposal(
        cls,
        session: Session,
        employee_id: str,
        current_salary: float,
        proposed_salary: float,
        reason_code: str,
        justification_notes: str,
        evidence_summary: Dict[str, Any],
        related_disparity_findings: Dict[str, Any],
        proposed_effective_date: date,
        created_by: str,
        actor_role: str = "HR_PARTNER",
        initial_status: str = "DRAFT",
        custom_id: Optional[str] = None
    ) -> AdjustmentProposal:
        """Creates a new adjustment proposal and logs creation audit event."""
        year = proposed_effective_date.year if isinstance(proposed_effective_date, date) else 2026
        if custom_id:
            proposal_id = custom_id
        else:
            # Sync counter with highest existing ID in DB so restarts never collide
            prefix = f"ADJ-{year}-"
            existing_ids = session.query(AdjustmentProposal.proposal_id).filter(
                AdjustmentProposal.proposal_id.like(f"{prefix}%")
            ).all()
            max_seq = 0
            for (pid,) in existing_ids:
                suffix = pid[len(prefix):]
                if suffix.isdigit():
                    max_seq = max(max_seq, int(suffix))
            if cls._proposal_counter < max_seq:
                cls._proposal_counter = max_seq
            proposal_id = cls.generate_proposal_id(year)

        adj_amount = round(proposed_salary - current_salary, 2)
        adj_pct = round((adj_amount / current_salary) * 100.0, 2) if current_salary > 0 else 0.0

        ev_str = json.dumps(evidence_summary)
        disp_str = json.dumps(related_disparity_findings)

        proposal = AdjustmentProposal(
            proposal_id=proposal_id,
            employee_id=employee_id,
            current_salary=current_salary,
            proposed_salary=proposed_salary,
            adjustment_amount=adj_amount,
            adjustment_percentage=adj_pct,
            reason_code=reason_code,
            justification_notes=justification_notes,
            evidence_summary=ev_str,
            related_disparity_findings=disp_str,
            proposed_effective_date=proposed_effective_date,
            approval_status=initial_status,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        session.add(proposal)
        session.flush()

        AuditLogger.log_event(
            session=session,
            entity_name="AdjustmentProposal",
            entity_id=proposal_id,
            event_type="PROPOSAL_CREATED",
            actor_id=created_by,
            actor_role=actor_role,
            new_state={"status": initial_status, "proposed_salary": proposed_salary, "adj_amount": adj_amount},
            notes=f"Proposal created for employee {employee_id}."
        )
        return proposal

    @classmethod
    def submit_for_review(
        cls,
        session: Session,
        proposal_id: str,
        submitted_by: str,
        actor_role: str = "HR_PARTNER",
        notes: Optional[str] = None
    ) -> AdjustmentProposal:
        """Transitions proposal from DRAFT -> PENDING_REVIEW."""
        proposal = session.query(AdjustmentProposal).filter_by(proposal_id=proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        if proposal.approval_status != "DRAFT":
            raise InvalidLifecycleTransitionException(
                f"Cannot submit proposal '{proposal_id}' for review from status '{proposal.approval_status}'."
            )

        old_status = proposal.approval_status
        proposal.approval_status = "PENDING_REVIEW"
        session.flush()

        AuditLogger.log_event(
            session=session,
            entity_name="AdjustmentProposal",
            entity_id=proposal_id,
            event_type="SUBMITTED_FOR_REVIEW",
            actor_id=submitted_by,
            actor_role=actor_role,
            old_state={"status": old_status},
            new_state={"status": "PENDING_REVIEW"},
            notes=notes or "Submitted for executive review."
        )
        return proposal

    @classmethod
    def approve_proposal(
        cls,
        session: Session,
        proposal_id: str,
        reviewed_by: str,
        actor_role: str = "MANAGER",
        review_notes: Optional[str] = None,
        apply_salary_update: bool = True
    ) -> AdjustmentProposal:
        """
        Transitions proposal from PENDING_REVIEW -> APPROVED.
        Optionally creates a new SalaryRecord reflecting the approved compensation.
        """
        proposal = session.query(AdjustmentProposal).filter_by(proposal_id=proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        if proposal.approval_status != "PENDING_REVIEW":
            raise InvalidLifecycleTransitionException(
                f"Cannot approve proposal '{proposal_id}' from status '{proposal.approval_status}'. Must be in PENDING_REVIEW."
            )

        old_status = proposal.approval_status
        now = datetime.utcnow()
        proposal.approval_status = "APPROVED"
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = now
        proposal.review_notes = review_notes or "Adjustment approved."

        # Audit event for approval
        AuditLogger.log_event(
            session=session,
            entity_name="AdjustmentProposal",
            entity_id=proposal_id,
            event_type="PROPOSAL_APPROVED",
            actor_id=reviewed_by,
            actor_role=actor_role,
            old_state={"status": old_status},
            new_state={"status": "APPROVED", "reviewed_at": now.isoformat()},
            notes=review_notes
        )

        if apply_salary_update:
            # Create new historical SalaryRecord
            emp = session.query(Employee).filter_by(employee_id=proposal.employee_id).first()
            if emp:
                base_sal_id = f"SAL-{emp.employee_id}-{proposal.proposed_effective_date.year:04d}-{proposal.proposed_effective_date.month:02d}"
                sal_id = base_sal_id
                suffix_idx = 2
                while session.query(SalaryRecord).filter_by(salary_id=sal_id).first() is not None:
                    sal_id = f"{base_sal_id}-{suffix_idx}"
                    suffix_idx += 1
                sal_record = SalaryRecord(
                    salary_id=sal_id,
                    employee_id=emp.employee_id,
                    base_salary=proposal.proposed_salary,
                    currency="USD",
                    fte=emp.fte,
                    pay_frequency="ANNUAL",
                    normalized_salary=proposal.proposed_salary,
                    normalized_currency="USD",
                    effective_date=proposal.proposed_effective_date,
                    change_reason="EQUITY_CORRECTION",
                    created_at=now
                )
                session.add(sal_record)
                session.flush()

                AuditLogger.log_event(
                    session=session,
                    entity_name="SalaryRecord",
                    entity_id=sal_id,
                    event_type="SALARY_UPDATED",
                    actor_id=reviewed_by,
                    actor_role=actor_role,
                    new_state={"salary": proposal.proposed_salary, "change_reason": "EQUITY_CORRECTION"},
                    notes=f"Applied approved adjustment proposal {proposal_id}."
                )

        session.flush()
        return proposal

    @classmethod
    def reject_proposal(
        cls,
        session: Session,
        proposal_id: str,
        reviewed_by: str,
        actor_role: str = "MANAGER",
        review_notes: Optional[str] = None
    ) -> AdjustmentProposal:
        """Transitions proposal from PENDING_REVIEW -> REJECTED."""
        proposal = session.query(AdjustmentProposal).filter_by(proposal_id=proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        if proposal.approval_status != "PENDING_REVIEW":
            raise InvalidLifecycleTransitionException(
                f"Cannot reject proposal '{proposal_id}' from status '{proposal.approval_status}'. Must be in PENDING_REVIEW."
            )

        old_status = proposal.approval_status
        now = datetime.utcnow()
        proposal.approval_status = "REJECTED"
        proposal.reviewed_by = reviewed_by
        proposal.reviewed_at = now
        proposal.review_notes = review_notes or "Adjustment rejected."

        AuditLogger.log_event(
            session=session,
            entity_name="AdjustmentProposal",
            entity_id=proposal_id,
            event_type="PROPOSAL_REJECTED",
            actor_id=reviewed_by,
            actor_role=actor_role,
            old_state={"status": old_status},
            new_state={"status": "REJECTED", "reviewed_at": now.isoformat()},
            notes=review_notes
        )
        session.flush()
        return proposal
