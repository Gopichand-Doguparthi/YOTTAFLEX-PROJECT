"""
Compensation Band Query Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import CompensationBand
from src.api.schemas import CompensationBandSchema

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
