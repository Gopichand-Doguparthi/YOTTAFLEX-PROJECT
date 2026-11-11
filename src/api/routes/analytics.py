"""
Analytics API Endpoints.
Provides executive summaries, salary distributions, role and location statistics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np

from src.database.session import get_db
from src.database.models import Employee, SalaryRecord, CompensationBand, AdjustmentProposal

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def get_executive_summary(db: Session = Depends(get_db)):
    """Returns top-level KPIs for executive dashboards."""
    total_employees = db.query(Employee).count()
    total_salary_records = db.query(SalaryRecord).count()
    total_bands = db.query(CompensationBand).count()
    total_proposals = db.query(AdjustmentProposal).count()
    pending_proposals = db.query(AdjustmentProposal).filter_by(approval_status="PENDING_REVIEW").count()
    approved_proposals = db.query(AdjustmentProposal).filter_by(approval_status="APPROVED").count()
    rejected_proposals = db.query(AdjustmentProposal).filter_by(approval_status="REJECTED").count()

    # Average normalized salary for 2026
    avg_salary_res = db.query(func.avg(SalaryRecord.normalized_salary)).filter(
        SalaryRecord.effective_date >= "2026-01-01"
    ).scalar()
    avg_salary = round(float(avg_salary_res), 2) if avg_salary_res else 0.0

    return {
        "total_employees": total_employees,
        "total_salary_records": total_salary_records,
        "total_compensation_bands": total_bands,
        "average_salary_usd": avg_salary,
        "total_proposals": total_proposals,
        "pending_proposals": pending_proposals,
        "approved_proposals": approved_proposals,
        "rejected_proposals": rejected_proposals
    }


@router.get("/distributions")
def get_salary_distributions(db: Session = Depends(get_db)):
    """Returns salary distribution by department and location."""
    # Query latest salary per employee
    salaries = db.query(
        Employee.department,
        Employee.current_location_id,
        SalaryRecord.normalized_salary
    ).join(SalaryRecord, Employee.employee_id == SalaryRecord.employee_id).filter(
        SalaryRecord.effective_date >= "2026-01-01"
    ).all()

    dept_stats = {}
    loc_stats = {}

    for dept, loc, sal in salaries:
        dept_stats.setdefault(dept, []).append(sal)
        loc_stats.setdefault(loc, []).append(sal)

    dept_summary = [
        {
            "department": k,
            "count": len(v),
            "median_salary": round(float(np.median(v)), 2),
            "mean_salary": round(float(np.mean(v)), 2),
            "min_salary": round(float(np.min(v)), 2),
            "max_salary": round(float(np.max(v)), 2)
        }
        for k, v in dept_stats.items()
    ]

    loc_summary = [
        {
            "location_id": k,
            "count": len(v),
            "median_salary": round(float(np.median(v)), 2),
            "mean_salary": round(float(np.mean(v)), 2)
        }
        for k, v in loc_stats.items()
    ]

    return {
        "department_distribution": dept_summary,
        "location_distribution": loc_summary
    }
