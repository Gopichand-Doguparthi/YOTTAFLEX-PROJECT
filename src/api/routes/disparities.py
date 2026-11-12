"""
Disparity Detection and Cohort Equity API Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import numpy as np

from src.database.session import get_db
from src.database.models import (
    Employee, SalaryRecord, CompensationBand, PerformanceEvidence, Tenure
)
from src.engine.disparity_detector import DisparityDetector
from src.engine.currency_normalizer import (
    CurrencyNormalizer, MissingCurrencyConversionException, select_effective_band
)
from src.api.schemas import DisparityResultSchema

router = APIRouter(prefix="/disparities", tags=["Disparity Analysis"])


@router.get("", response_model=List[DisparityResultSchema])
def get_detected_disparities(
    only_unexplained: bool = Query(True, description="Filter only unexplained disparities"),
    department: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Executes multi-factor disparity evaluation across employees and returns categorized findings."""
    detector = DisparityDetector()

    # Load recent data
    emp_query = db.query(Employee)
    if department:
        emp_query = emp_query.filter(Employee.department == department)
    if location_id:
        emp_query = emp_query.filter(Employee.current_location_id == location_id)
    employees = emp_query.all()

    salaries = db.query(SalaryRecord).filter(SalaryRecord.effective_date >= "2026-01-01").all()
    latest_sals = {}
    for s in salaries:
        if s.employee_id not in latest_sals or s.effective_date > latest_sals[s.employee_id].effective_date:
            latest_sals[s.employee_id] = s

    all_bands = db.query(CompensationBand).all()
    bands_by_key = {}
    for b in all_bands:
        bands_by_key.setdefault((b.role_id, b.level_id, b.location_id), []).append(b)

    curr_norm = CurrencyNormalizer()
    curr_norm.load_from_db(db)

    # Group cohorts for median
    cohort_salaries = {}
    for emp in employees:
        sal = latest_sals.get(emp.employee_id)
        if sal:
            key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
            cohort_salaries.setdefault(key, []).append(sal.normalized_salary)

    cohort_medians = {k: float(np.median(v)) for k, v in cohort_salaries.items()}
    cohort_sizes = {k: len(v) for k, v in cohort_salaries.items()}

    perfs = db.query(PerformanceEvidence).all()
    latest_perf = {}
    for p in perfs:
        if p.employee_id not in latest_perf or p.effective_date > latest_perf[p.employee_id].effective_date:
            latest_perf[p.employee_id] = p

    tenures = {t.employee_id: t for t in db.query(Tenure).all()}

    results = []
    for emp in employees:
        sal = latest_sals.get(emp.employee_id)
        if not sal:
            continue

        cohort_key = f"{emp.current_role_id}::{emp.current_level_id}::{emp.current_location_id}"
        med_sal = cohort_medians.get(cohort_key, sal.normalized_salary)
        size = cohort_sizes.get(cohort_key, 1)

        key_tuple = (emp.current_role_id, emp.current_level_id, emp.current_location_id)
        band = select_effective_band(
            bands_by_key.get(key_tuple, []),
            emp.current_role_id,
            emp.current_level_id,
            emp.current_location_id,
            on_date=sal.effective_date,
        )
        if band:
            try:
                b_min, b_mid, b_max = curr_norm.convert_band_to_reporting(
                    band, to_currency="USD", on_date=sal.effective_date
                )
            except MissingCurrencyConversionException:
                b_min, b_mid, b_max = med_sal * 0.8, med_sal, med_sal * 1.2
        else:
            b_min, b_mid, b_max = med_sal * 0.8, med_sal, med_sal * 1.2

        perf = latest_perf.get(emp.employee_id)
        rating = perf.rating_score if perf else None
        tenure_rec = tenures.get(emp.employee_id)
        c_tenure = tenure_rec.tenure_in_company_years if tenure_rec else 1.0
        r_tenure = tenure_rec.tenure_in_role_years if tenure_rec else 1.0

        eval_res = detector.evaluate_employee(
            employee_id=emp.employee_id,
            normalized_salary=sal.normalized_salary,
            band_min=b_min,
            band_mid=b_mid,
            band_max=b_max,
            cohort_median_salary=med_sal,
            cohort_size=size,
            performance_rating=rating,
            tenure_in_role_years=r_tenure,
            tenure_in_company_years=c_tenure
        )

        if only_unexplained and not eval_res.is_disparity:
            continue

        results.append(eval_res.to_dict())
        if len(results) >= limit:
            break

    return results
