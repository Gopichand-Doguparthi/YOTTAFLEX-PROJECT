"""
ReviewCase REST API Endpoints.
Manages human investigation workflow for flagged compensation disparities.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import ReviewCase, Employee
from src.api.schemas import ReviewCaseCreateRequest, ReviewCaseUpdateRequest, ReviewCaseSchema
from src.api.auth import get_current_user, require_roles
from src.workflow.audit_logger import AuditLogger

router = APIRouter(prefix="/review-cases", tags=["Review Cases"])

ALLOWED_CASE_TRANSITIONS = {
    "OPEN": {"OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED"},
    "IN_REVIEW": {"IN_REVIEW", "ESCALATED", "RESOLVED"},
    "ESCALATED": {"ESCALATED", "IN_REVIEW", "RESOLVED"},
    "RESOLVED": {"RESOLVED", "REOPENED"},
    "REOPENED": {"REOPENED", "IN_REVIEW", "ESCALATED", "RESOLVED"},
}


@router.get("", response_model=List[ReviewCaseSchema])
def list_review_cases(
    status: Optional[str] = Query(None, description="OPEN, IN_REVIEW, ESCALATED, RESOLVED, REOPENED"),
    employee_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Lists human disparity review cases with filtering and pagination."""
    query = db.query(ReviewCase)
    if status:
        query = query.filter(ReviewCase.status == status.upper())
    if employee_id:
        query = query.filter(ReviewCase.employee_id == employee_id)
    if assigned_to:
        query = query.filter(ReviewCase.assigned_to == assigned_to)
    return query.order_by(ReviewCase.updated_at.desc()).offset(offset).limit(limit).all()


@router.get("/{case_id}", response_model=ReviewCaseSchema)
def get_review_case(
    case_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Retrieves a single review case by case_id."""
    case = db.query(ReviewCase).filter(ReviewCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Review case '{case_id}' not found.")
    return case


@router.post("", response_model=ReviewCaseSchema, status_code=201)
def create_review_case(
    req: ReviewCaseCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "MANAGER", "SYSTEM_ADMIN", "COMP_COMMITTEE")),
):
    """Opens a new human review case for an employee (prevents duplicate cases per employee)."""
    emp = db.query(Employee).filter(Employee.employee_id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{req.employee_id}' not found.")
    if db.query(ReviewCase).filter(ReviewCase.employee_id == req.employee_id).first():
        raise HTTPException(status_code=409, detail=f"Review case already exists for employee '{req.employee_id}'.")

    case_id = f"CASE-{req.employee_id}"
    case = ReviewCase(
        case_id=case_id,
        employee_id=req.employee_id,
        status="OPEN",
        assigned_to=req.assigned_to or current_user["sub"],
        comments=req.comments,
    )
    db.add(case)
    AuditLogger.log_event(
        session=db,
        entity_name="ReviewCase",
        entity_id=case_id,
        event_type="REVIEW_CASE_CREATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        new_state={"status": "OPEN", "employee_id": req.employee_id, "assigned_to": case.assigned_to},
        notes=req.comments or "Opened review case via API.",
    )
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}", response_model=ReviewCaseSchema)
def update_review_case(
    case_id: str,
    req: ReviewCaseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "MANAGER", "SYSTEM_ADMIN", "COMP_COMMITTEE")),
):
    """Transitions review case status or updates assignment/comments with state validation and audit logging."""
    case = db.query(ReviewCase).filter(ReviewCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Review case '{case_id}' not found.")

    old_state = {"status": case.status, "assigned_to": case.assigned_to, "comments": case.comments}
    updates = req.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] is not None:
        target_status = updates["status"]
        allowed = ALLOWED_CASE_TRANSITIONS.get(case.status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state transition from '{case.status}' to '{target_status}'.",
            )
        case.status = target_status

    if "assigned_to" in updates:
        case.assigned_to = updates["assigned_to"]
    if "comments" in updates:
        case.comments = updates["comments"]

    AuditLogger.log_event(
        session=db,
        entity_name="ReviewCase",
        entity_id=case.case_id,
        event_type="REVIEW_CASE_UPDATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        old_state=old_state,
        new_state={"status": case.status, "assigned_to": case.assigned_to},
        notes=case.comments or "Updated review case via API.",
    )
    db.commit()
    db.refresh(case)
    return case
