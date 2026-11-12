"""
Compensation Band Query Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import CompensationBand, Role, Level, Location
from src.api.schemas import CompensationBandSchema, BandCreateRequest, BandUpdateRequest
from src.api.auth import require_roles
from src.workflow.audit_logger import AuditLogger

router = APIRouter(prefix="/bands", tags=["Compensation Bands"])


@router.get("", response_model=List[CompensationBandSchema])
def list_compensation_bands(
    role_id: Optional[str] = None,
    level_id: Optional[str] = None,
    location_id: Optional[str] = None,
    status: Optional[str] = Query("ACTIVE", description="ACTIVE, EXPIRED, DRAFT, or ALL"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves compensation bands filtered by role, level, location, and lifecycle status."""
    query = db.query(CompensationBand)
    if role_id:
        query = query.filter(CompensationBand.role_id == role_id)
    if level_id:
        query = query.filter(CompensationBand.level_id == level_id)
    if location_id:
        query = query.filter(CompensationBand.location_id == location_id)
    if status and status.upper() != "ALL":
        query = query.filter(CompensationBand.status == status.upper())

    return query.offset(offset).limit(limit).all()


@router.post("", response_model=CompensationBandSchema, status_code=201)
def create_compensation_band(
    req: BandCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "SYSTEM_ADMIN", "COMP_COMMITTEE")),
):
    """Creates a new effective-dated compensation band with spread and overlap validation."""
    if db.query(CompensationBand).filter(CompensationBand.band_id == req.band_id).first():
        raise HTTPException(status_code=409, detail=f"Band ID '{req.band_id}' already exists.")
    if not (req.min_salary < req.mid_salary < req.max_salary):
        raise HTTPException(status_code=400, detail="Invalid spread: must satisfy min_salary < mid_salary < max_salary.")
    if req.effective_end_date and req.effective_start_date > req.effective_end_date:
        raise HTTPException(status_code=400, detail="effective_start_date cannot be after effective_end_date.")
    if not db.query(Role).filter(Role.role_id == req.role_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid role_id '{req.role_id}'.")
    if not db.query(Level).filter(Level.level_id == req.level_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid level_id '{req.level_id}'.")
    if not db.query(Location).filter(Location.location_id == req.location_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid location_id '{req.location_id}'.")

    if req.status == "ACTIVE":
        existing_active = db.query(CompensationBand).filter(
            CompensationBand.role_id == req.role_id,
            CompensationBand.level_id == req.level_id,
            CompensationBand.location_id == req.location_id,
            CompensationBand.status == "ACTIVE",
        ).all()
        for b in existing_active:
            b_end = b.effective_end_date
            req_end = req.effective_end_date
            if (b_end is None or req.effective_start_date <= b_end) and (req_end is None or b.effective_start_date <= req_end):
                raise HTTPException(
                    status_code=400,
                    detail=f"Overlapping ACTIVE band '{b.band_id}' exists for this role/level/location window.",
                )

    band = CompensationBand(**req.model_dump())
    db.add(band)
    AuditLogger.log_event(
        session=db,
        entity_name="CompensationBand",
        entity_id=band.band_id,
        event_type="BAND_CREATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        new_state={"min": band.min_salary, "mid": band.mid_salary, "max": band.max_salary, "status": band.status},
    )
    db.commit()
    db.refresh(band)
    return band


@router.patch("/{band_id}", response_model=CompensationBandSchema)
def update_compensation_band(
    band_id: str,
    req: BandUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "SYSTEM_ADMIN", "COMP_COMMITTEE")),
):
    """Updates an existing compensation band's spread or lifecycle status with audit logging."""
    band = db.query(CompensationBand).filter(CompensationBand.band_id == band_id).first()
    if not band:
        raise HTTPException(status_code=404, detail=f"Band '{band_id}' not found.")

    updates = req.model_dump(exclude_unset=True)
    new_min = updates.get("min_salary", band.min_salary)
    new_mid = updates.get("mid_salary", band.mid_salary)
    new_max = updates.get("max_salary", band.max_salary)
    if not (new_min < new_mid < new_max):
        raise HTTPException(status_code=400, detail="Invalid spread: must satisfy min_salary < mid_salary < max_salary.")

    old_state = {"min": band.min_salary, "mid": band.mid_salary, "max": band.max_salary, "status": band.status}
    for k, v in updates.items():
        setattr(band, k, v)

    AuditLogger.log_event(
        session=db,
        entity_name="CompensationBand",
        entity_id=band.band_id,
        event_type="BAND_UPDATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        old_state=old_state,
        new_state=updates,
    )
    db.commit()
    db.refresh(band)
    return band
