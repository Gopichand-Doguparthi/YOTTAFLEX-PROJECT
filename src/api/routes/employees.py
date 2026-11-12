"""
Employee Directory and Compensation Profile Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import Employee, SalaryRecord, CompensationBand, Role, Level, Location
from src.api.schemas import (
    EmployeeSchema, EmployeeDetailSchema, EmployeeCreateRequest, EmployeeUpdateRequest
)
from src.api.auth import require_roles
from src.workflow.audit_logger import AuditLogger
from src.engine.compa_ratio import CompaRatioCalculator
from src.engine.within_band import WithinBandCalculator
from src.engine.currency_normalizer import (
    CurrencyNormalizer, MissingCurrencyConversionException, select_effective_band
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[EmployeeSchema])
def list_employees(
    department: Optional[str] = None,
    role_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves paginated employee directory with optional filters."""
    query = db.query(Employee)
    if department:
        query = query.filter(Employee.department == department)
    if role_id:
        query = query.filter(Employee.current_role_id == role_id)
    if location_id:
        query = query.filter(Employee.current_location_id == location_id)

    return query.offset(offset).limit(limit).all()


@router.get("/{employee_id}", response_model=EmployeeDetailSchema)
def get_employee_detail(employee_id: str, db: Session = Depends(get_db)):
    """Retrieves comprehensive employee profile with historical salary records and compa-ratio."""
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    sals = db.query(SalaryRecord).filter(SalaryRecord.employee_id == employee_id).order_by(SalaryRecord.effective_date.desc()).all()
    latest_sal_rec = sals[0] if sals else None
    latest_sal = latest_sal_rec.normalized_salary if latest_sal_rec else None

    # Benchmark against effective-dated band converted to USD reporting currency
    candidate_bands = db.query(CompensationBand).filter(
        CompensationBand.role_id == emp.current_role_id,
        CompensationBand.level_id == emp.current_level_id,
        CompensationBand.location_id == emp.current_location_id,
    ).all()
    ref_date = latest_sal_rec.effective_date if latest_sal_rec else None
    band = select_effective_band(
        candidate_bands, emp.current_role_id, emp.current_level_id, emp.current_location_id, on_date=ref_date
    )

    cr = None
    wbp = None
    if latest_sal and band:
        curr_norm = CurrencyNormalizer()
        curr_norm.load_from_db(db)
        try:
            b_min, b_mid, b_max = curr_norm.convert_band_to_reporting(band, to_currency="USD", on_date=ref_date)
            cr = CompaRatioCalculator.calculate(latest_sal, b_mid)
            wbp = WithinBandCalculator.calculate(latest_sal, b_min, b_max)
        except MissingCurrencyConversionException:
            cr = None
            wbp = None

    return EmployeeDetailSchema(
        employee_id=emp.employee_id,
        first_name=emp.first_name,
        last_name=emp.last_name,
        email=emp.email,
        department=emp.department,
        current_role_id=emp.current_role_id,
        current_level_id=emp.current_level_id,
        current_location_id=emp.current_location_id,
        hire_date=emp.hire_date,
        employment_type=emp.employment_type,
        fte=emp.fte,
        is_active=emp.is_active,
        salary_records=sals,
        current_normalized_salary=latest_sal,
        compa_ratio=cr,
        within_band_position=wbp
    )


@router.post("", response_model=EmployeeSchema, status_code=201)
def create_employee(
    req: EmployeeCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "SYSTEM_ADMIN")),
):
    """Creates a new employee with duplicate ID/email and foreign-key validation."""
    if db.query(Employee).filter(Employee.employee_id == req.employee_id).first():
        raise HTTPException(status_code=409, detail=f"Employee ID '{req.employee_id}' already exists.")
    if db.query(Employee).filter(Employee.email == req.email).first():
        raise HTTPException(status_code=409, detail=f"Employee email '{req.email}' already exists.")
    if not db.query(Role).filter(Role.role_id == req.current_role_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid role_id '{req.current_role_id}'.")
    if not db.query(Level).filter(Level.level_id == req.current_level_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid level_id '{req.current_level_id}'.")
    if not db.query(Location).filter(Location.location_id == req.current_location_id).first():
        raise HTTPException(status_code=400, detail=f"Invalid location_id '{req.current_location_id}'.")

    emp = Employee(**req.model_dump(), is_active=True)
    db.add(emp)
    AuditLogger.log_event(
        session=db,
        entity_name="Employee",
        entity_id=emp.employee_id,
        event_type="EMPLOYEE_CREATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        new_state={"role_id": emp.current_role_id, "level_id": emp.current_level_id, "fte": emp.fte},
    )
    db.commit()
    db.refresh(emp)
    return emp


@router.patch("/{employee_id}", response_model=EmployeeSchema)
def update_employee(
    employee_id: str,
    req: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "SYSTEM_ADMIN")),
):
    """Updates employee attributes or deactivates an employee with audit trail logging."""
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    old_state = {
        "department": emp.department,
        "role_id": emp.current_role_id,
        "level_id": emp.current_level_id,
        "location_id": emp.current_location_id,
        "fte": emp.fte,
        "is_active": emp.is_active,
    }
    updates = req.model_dump(exclude_unset=True)
    if "current_role_id" in updates and not db.query(Role).filter(Role.role_id == updates["current_role_id"]).first():
        raise HTTPException(status_code=400, detail=f"Invalid role_id '{updates['current_role_id']}'.")
    if "current_level_id" in updates and not db.query(Level).filter(Level.level_id == updates["current_level_id"]).first():
        raise HTTPException(status_code=400, detail=f"Invalid level_id '{updates['current_level_id']}'.")
    if "current_location_id" in updates and not db.query(Location).filter(Location.location_id == updates["current_location_id"]).first():
        raise HTTPException(status_code=400, detail=f"Invalid location_id '{updates['current_location_id']}'.")

    for k, v in updates.items():
        setattr(emp, k, v)

    AuditLogger.log_event(
        session=db,
        entity_name="Employee",
        entity_id=emp.employee_id,
        event_type="EMPLOYEE_UPDATED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        old_state=old_state,
        new_state=updates,
    )
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("HR_PARTNER", "SYSTEM_ADMIN")),
):
    """Deletes an employee record and logs an immutable audit event."""
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    old_state = {
        "name": f"{emp.first_name} {emp.last_name}",
        "department": emp.department,
        "role_id": emp.current_role_id,
        "level_id": emp.current_level_id,
        "location_id": emp.current_location_id,
    }
    db.delete(emp)
    AuditLogger.log_event(
        session=db,
        entity_name="Employee",
        entity_id=employee_id,
        event_type="EMPLOYEE_DELETED",
        actor_id=current_user["sub"],
        actor_role=current_user["role"],
        old_state=old_state,
        new_state={"deleted": True},
        notes=f"Employee {employee_id} permanently deleted.",
    )
    db.commit()
    return {"status": "deleted", "employee_id": employee_id}
