"""
Employee Directory and Compensation Profile Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.database.models import Employee, SalaryRecord, CompensationBand
from src.api.schemas import EmployeeSchema, EmployeeDetailSchema
from src.engine.compa_ratio import CompaRatioCalculator
from src.engine.within_band import WithinBandCalculator

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
    latest_sal = sals[0].normalized_salary if sals else None

    # Benchmark against active band
    band = db.query(CompensationBand).filter(
        CompensationBand.role_id == emp.current_role_id,
        CompensationBand.level_id == emp.current_level_id,
        CompensationBand.location_id == emp.current_location_id,
        CompensationBand.status == "ACTIVE"
    ).first()

    cr = None
    wbp = None
    if latest_sal and band:
        cr = CompaRatioCalculator.calculate(latest_sal, band.mid_salary)
        wbp = WithinBandCalculator.calculate(latest_sal, band.min_salary, band.max_salary)

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
