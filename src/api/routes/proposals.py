"""
Adjustment Proposals and Approval Lifecycle API Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import AdjustmentProposal, Employee, SalaryRecord, ApprovalEvent
from src.api.schemas import (
    AdjustmentProposalSchema, ProposalCreateRequest, ProposalReviewRequest
)
from src.workflow.proposal_manager import ProposalManager, UnauthorizedApprovalException

router = APIRouter(prefix="/proposals", tags=["Adjustment Proposals"])


@router.get("", response_model=List[AdjustmentProposalSchema])
def list_proposals(
    status: Optional[str] = Query(None, description="DRAFT, PENDING_REVIEW, APPROVED, REJECTED"),
    employee_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves list of adjustment proposals."""
    query = db.query(AdjustmentProposal)
    if status:
        query = query.filter(AdjustmentProposal.approval_status == status.upper())
    if employee_id:
        query = query.filter(AdjustmentProposal.employee_id == employee_id)

    return query.order_by(AdjustmentProposal.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=AdjustmentProposalSchema)
def create_proposal(req: ProposalCreateRequest, db: Session = Depends(get_db)):
    """Creates a new adjustment proposal in DRAFT status."""
    emp = db.query(Employee).filter(Employee.employee_id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{req.employee_id}' not found.")

    latest_sal = db.query(SalaryRecord).filter(
        SalaryRecord.employee_id == req.employee_id
    ).order_by(SalaryRecord.effective_date.desc()).first()
    curr_sal = latest_sal.normalized_salary if latest_sal else 100000.0

    proposal = ProposalManager.create_proposal(
        session=db,
        employee_id=req.employee_id,
        current_salary=curr_sal,
        proposed_salary=req.proposed_salary,
        reason_code=req.reason_code,
        justification_notes=req.justification_notes,
        evidence_summary={"manual_submission": True},
        related_disparity_findings={"status": "MANUAL_PROPOSAL"},
        proposed_effective_date=req.proposed_effective_date,
        created_by=req.created_by
    )
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/{proposal_id}/submit", response_model=AdjustmentProposalSchema)
def submit_proposal_for_review(proposal_id: str, submitted_by: str = "hr.partner@company.org", db: Session = Depends(get_db)):
    """Submits a proposal from DRAFT -> PENDING_REVIEW."""
    try:
        prop = ProposalManager.submit_for_review(db, proposal_id, submitted_by=submitted_by)
        db.commit()
        db.refresh(prop)
        return prop
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{proposal_id}/review", response_model=AdjustmentProposalSchema)
def review_proposal(proposal_id: str, req: ProposalReviewRequest, db: Session = Depends(get_db)):
    """Approves or rejects a proposal (PENDING_REVIEW -> APPROVED / REJECTED)."""
    try:
        if req.decision == "APPROVED":
            prop = ProposalManager.approve_proposal(
                session=db,
                proposal_id=proposal_id,
                reviewed_by=req.reviewed_by,
                actor_role=req.actor_role,
                review_notes=req.review_notes,
                apply_salary_update=True
            )
        else:
            prop = ProposalManager.reject_proposal(
                session=db,
                proposal_id=proposal_id,
                reviewed_by=req.reviewed_by,
                actor_role=req.actor_role,
                review_notes=req.review_notes
            )
        db.commit()
        db.refresh(prop)
        return prop
    except UnauthorizedApprovalException as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/audit/events")
def list_audit_events(
    entity_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Retrieves immutable audit trail ledger events."""
    query = db.query(ApprovalEvent)
    if entity_id:
        query = query.filter(ApprovalEvent.entity_id == entity_id)

    events = query.order_by(ApprovalEvent.timestamp.desc()).limit(limit).all()
    return events
