"""
Pydantic Request and Response Schemas for FastAPI backend.
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Location & Role & Level Schemas
class LocationSchema(BaseModel):
    location_id: str
    location_name: str
    country: str
    currency: str
    geo_tier: str
    cost_of_living_index: float

    class Config:
        from_attributes = True


class RoleSchema(BaseModel):
    role_id: str
    role_title: str
    job_family: str
    job_function: str
    is_active: bool

    class Config:
        from_attributes = True


class LevelSchema(BaseModel):
    level_id: str
    level_code: str
    level_name: str
    rank: int

    class Config:
        from_attributes = True


# Compensation Band Schema
class CompensationBandSchema(BaseModel):
    band_id: str
    role_id: str
    level_id: str
    location_id: str
    currency: str
    min_salary: float
    mid_salary: float
    max_salary: float
    effective_start_date: date
    effective_end_date: Optional[date]
    status: str

    class Config:
        from_attributes = True


# Salary Record Schema
class SalaryRecordSchema(BaseModel):
    salary_id: str
    employee_id: str
    base_salary: float
    currency: str
    fte: float
    pay_frequency: str
    normalized_salary: float
    normalized_currency: str
    effective_date: date
    end_date: Optional[date]
    change_reason: str
    benchmark_band_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Employee Profile Schema
class EmployeeSchema(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    department: str
    current_role_id: str
    current_level_id: str
    current_location_id: str
    hire_date: date
    employment_type: str
    fte: float
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeDetailSchema(EmployeeSchema):
    salary_records: List[SalaryRecordSchema] = []
    current_normalized_salary: Optional[float] = None
    compa_ratio: Optional[float] = None
    within_band_position: Optional[float] = None


# Proposal Schemas
class ProposalCreateRequest(BaseModel):
    employee_id: str
    proposed_salary: float
    reason_code: str
    justification_notes: str
    proposed_effective_date: date
    created_by: str = "hr.partner@company.org"


class ProposalReviewRequest(BaseModel):
    reviewed_by: str
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    review_notes: Optional[str] = None


class AdjustmentProposalSchema(BaseModel):
    proposal_id: str
    employee_id: str
    current_salary: float
    proposed_salary: float
    adjustment_amount: float
    adjustment_percentage: float
    reason_code: str
    justification_notes: str
    evidence_summary: str
    related_disparity_findings: str
    proposed_effective_date: date
    approval_status: str
    created_by: str
    created_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]

    class Config:
        from_attributes = True


# Disparity Result Schema
class DisparityResultSchema(BaseModel):
    employee_id: str
    status: str
    compa_ratio: float
    within_band_position: float
    deviation_from_cohort_median_pct: float
    cohort_size: int
    primary_reason: str
    supporting_evidence: Dict[str, Any]
    is_disparity: bool
    confidence_score: float


# Evaluation Summary Schema
class EvaluationSummarySchema(BaseModel):
    overall_metrics: Dict[str, Any]
    per_issue_metrics: Dict[str, Any]
    total_exceptions_detected: int
    total_disparities_detected: int
    total_ground_truth_samples: int
