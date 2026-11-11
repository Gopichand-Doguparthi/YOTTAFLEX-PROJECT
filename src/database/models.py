"""
SQLAlchemy 2.0 ORM Models for Compensation Equity & Disparity Analysis System.
Defines all 10 core business entities plus audit, exchange rate, comparability, and ground-truth tables.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime, Text,
    ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from src.database.session import Base


class Location(Base):
    """Geographic entity governing local currency, tiers, and cost-of-living."""
    __tablename__ = "locations"

    location_id = Column(String(16), primary_key=True)  # LOC-NYC, LOC-LON, etc.
    location_name = Column(String(128), nullable=False, unique=True)
    country = Column(String(3), nullable=False)  # ISO 3166-1 alpha-3
    currency = Column(String(3), nullable=False)  # ISO 4217
    geo_tier = Column(String(16), nullable=False)  # Tier-1, Tier-2, Tier-3
    cost_of_living_index = Column(Float, nullable=False, default=1.0)

    # Relationships
    employees = relationship("Employee", back_populates="location")
    compensation_bands = relationship("CompensationBand", back_populates="location")

    __table_args__ = (
        CheckConstraint("cost_of_living_index > 0", name="chk_col_index_pos"),
    )


class Role(Base):
    """Job profile categorized by job family and functional domain."""
    __tablename__ = "roles"

    role_id = Column(String(32), primary_key=True)  # ROLE-SWE, ROLE-DS, etc.
    role_title = Column(String(128), nullable=False, unique=True)
    job_family = Column(String(64), nullable=False)
    job_function = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    employees = relationship("Employee", back_populates="role")
    compensation_bands = relationship("CompensationBand", back_populates="role")


class Level(Base):
    """Standardized professional career ladder level."""
    __tablename__ = "levels"

    level_id = Column(String(16), primary_key=True)  # LVL-L1 .. LVL-L6, LVL-EXEC
    level_code = Column(String(16), nullable=False, unique=True)  # L1, L2, etc.
    level_name = Column(String(64), nullable=False)
    rank = Column(Integer, nullable=False, unique=True)  # 1 to 7

    # Relationships
    employees = relationship("Employee", back_populates="level")
    compensation_bands = relationship("CompensationBand", back_populates="level")

    __table_args__ = (
        CheckConstraint("rank >= 1", name="chk_level_rank_pos"),
    )


class CompensationBand(Base):
    """Effective-dated salary band establishing min, mid, max salary."""
    __tablename__ = "compensation_bands"

    band_id = Column(String(128), primary_key=True)  # BAND-<role>-<lvl>-<loc>-2026
    role_id = Column(String(32), ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    level_id = Column(String(16), ForeignKey("levels.level_id", ondelete="RESTRICT"), nullable=False)
    location_id = Column(String(16), ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False)
    currency = Column(String(3), nullable=False)
    min_salary = Column(Float, nullable=False)
    mid_salary = Column(Float, nullable=False)
    max_salary = Column(Float, nullable=False)
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date, nullable=True)
    status = Column(String(16), nullable=False, default="ACTIVE")  # ACTIVE, EXPIRED, DRAFT

    # Relationships
    role = relationship("Role", back_populates="compensation_bands")
    level = relationship("Level", back_populates="compensation_bands")
    location = relationship("Location", back_populates="compensation_bands")

    __table_args__ = (
        CheckConstraint("min_salary > 0 AND min_salary < mid_salary AND mid_salary < max_salary", name="chk_band_spread"),
        Index("idx_band_lookup", "role_id", "level_id", "location_id", "effective_start_date", "effective_end_date"),
    )


class Employee(Base):
    """Primary workforce individual record."""
    __tablename__ = "employees"

    employee_id = Column(String(32), primary_key=True)  # EMP-000001
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(128), nullable=False, unique=True)
    department = Column(String(64), nullable=False)
    current_role_id = Column(String(32), ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    current_level_id = Column(String(16), ForeignKey("levels.level_id", ondelete="RESTRICT"), nullable=False)
    current_location_id = Column(String(16), ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False)
    hire_date = Column(Date, nullable=False)
    employment_type = Column(String(20), nullable=False, default="FULL_TIME")  # FULL_TIME, PART_TIME, CONTRACT
    fte = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    role = relationship("Role", back_populates="employees")
    level = relationship("Level", back_populates="employees")
    location = relationship("Location", back_populates="employees")
    salary_records = relationship("SalaryRecord", back_populates="employee", cascade="all, delete-orphan")
    performance_records = relationship("PerformanceEvidence", back_populates="employee", cascade="all, delete-orphan", foreign_keys="PerformanceEvidence.employee_id")
    tenure = relationship("Tenure", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    promotions = relationship("Promotion", back_populates="employee", cascade="all, delete-orphan")
    proposals = relationship("AdjustmentProposal", back_populates="employee", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("fte > 0", name="chk_employee_fte_valid"),
        Index("idx_emp_role_lvl_loc", "current_role_id", "current_level_id", "current_location_id"),
    )


class SalaryRecord(Base):
    """Effective-dated compensation history record for an employee."""
    __tablename__ = "salary_records"

    salary_id = Column(String(64), primary_key=True)  # SAL-EMP-000001-2026-01
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    base_salary = Column(Float, nullable=False)  # in local currency
    currency = Column(String(3), nullable=False)
    fte = Column(Float, nullable=False, default=1.0)
    pay_frequency = Column(String(16), nullable=False, default="ANNUAL")  # ANNUAL, MONTHLY
    normalized_salary = Column(Float, nullable=False)  # in USD, 1.0 FTE annualized
    normalized_currency = Column(String(3), nullable=False, default="USD")
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    change_reason = Column(String(32), nullable=False)  # HIRE, ANNUAL_MERIT, PROMOTION, etc.
    benchmark_band_id = Column(String(128), ForeignKey("compensation_bands.band_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="salary_records")

    __table_args__ = (
        CheckConstraint("base_salary > 0 AND fte > 0 AND fte <= 1.0 AND normalized_salary > 0", name="chk_sal_positive"),
        Index("idx_sal_emp_eff", "employee_id", "effective_date"),
    )


class PerformanceEvidence(Base):
    """Documented review cycle performance evaluation."""
    __tablename__ = "performance_evidence"

    evidence_id = Column(String(64), primary_key=True)  # PERF-EMP-000001-2025-H2
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    review_cycle = Column(String(16), nullable=False)  # 2024-H1, 2024-H2, etc.
    rating_score = Column(Float, nullable=False)  # 1.0 to 5.0
    rating_label = Column(String(32), nullable=False)  # NEEDS_IMPROVEMENT, MEETS_EXPECTATIONS, etc.
    reviewer_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True)
    documented_skills_score = Column(Float, nullable=False, default=70.0)
    critical_initiative_count = Column(Integer, nullable=False, default=0)
    effective_date = Column(Date, nullable=False)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="performance_records")

    __table_args__ = (
        CheckConstraint("rating_score >= 1.0 AND rating_score <= 5.0", name="chk_rating_range"),
        CheckConstraint("documented_skills_score >= 0.0 AND documented_skills_score <= 100.0", name="chk_skill_score_range"),
        Index("idx_perf_emp_cycle", "employee_id", "review_cycle"),
    )


class Tenure(Base):
    """Tracks length of service and total experience metrics."""
    __tablename__ = "tenure_records"

    tenure_id = Column(String(64), primary_key=True)  # TEN-EMP-000001
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False, unique=True)
    company_start_date = Column(Date, nullable=False)
    role_start_date = Column(Date, nullable=False)
    years_of_experience_total = Column(Float, nullable=False, default=0.0)
    tenure_in_company_years = Column(Float, nullable=False, default=0.0)
    tenure_in_role_years = Column(Float, nullable=False, default=0.0)

    # Relationships
    employee = relationship("Employee", back_populates="tenure")

    __table_args__ = (
        CheckConstraint("years_of_experience_total >= 0.0", name="chk_exp_pos"),
        CheckConstraint("tenure_in_company_years >= 0.0", name="chk_comp_tenure_pos"),
        CheckConstraint("tenure_in_role_years >= 0.0", name="chk_role_tenure_pos"),
    )


class Promotion(Base):
    """Tracks career advancement promotions."""
    __tablename__ = "promotions"

    promotion_id = Column(String(64), primary_key=True)  # PROM-EMP-000001-202506
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    from_level_id = Column(String(16), ForeignKey("levels.level_id", ondelete="RESTRICT"), nullable=False)
    to_level_id = Column(String(16), ForeignKey("levels.level_id", ondelete="RESTRICT"), nullable=False)
    from_role_id = Column(String(32), ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    to_role_id = Column(String(32), ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False)
    promotion_date = Column(Date, nullable=False)
    previous_salary = Column(Float, nullable=False)
    new_salary = Column(Float, nullable=False)
    increase_percentage = Column(Float, nullable=False)
    approved_by = Column(String(64), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="promotions")


class AdjustmentProposal(Base):
    """Remediation proposal to correct compensation disparities."""
    __tablename__ = "adjustment_proposals"

    proposal_id = Column(String(32), primary_key=True)  # ADJ-2026-000001
    employee_id = Column(String(32), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    current_salary = Column(Float, nullable=False)
    proposed_salary = Column(Float, nullable=False)
    adjustment_amount = Column(Float, nullable=False)
    adjustment_percentage = Column(Float, nullable=False)
    reason_code = Column(String(32), nullable=False)  # INTERNAL_EQUITY, MARKET_PARITY, etc.
    justification_notes = Column(Text, nullable=False)
    evidence_summary = Column(Text, nullable=False)
    related_disparity_findings = Column(Text, nullable=False)
    proposed_effective_date = Column(Date, nullable=False)
    approval_status = Column(String(20), nullable=False, default="DRAFT")  # DRAFT, PENDING_REVIEW, APPROVED, REJECTED
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="proposals")

    __table_args__ = (
        CheckConstraint("current_salary > 0 AND proposed_salary > 0", name="chk_prop_salary_pos"),
        Index("idx_adj_status", "approval_status"),
    )


class ApprovalEvent(Base):
    """Append-only audit trail logging state mutations and approval events."""
    __tablename__ = "approval_events"

    event_id = Column(String(64), primary_key=True)  # EVT-20261111-000001
    entity_name = Column(String(32), nullable=False)  # AdjustmentProposal, SalaryRecord, etc.
    entity_id = Column(String(128), nullable=False)
    event_type = Column(String(32), nullable=False)  # CREATED, SUBMITTED_FOR_REVIEW, APPROVED, etc.
    actor_id = Column(String(64), nullable=False)
    actor_role = Column(String(32), nullable=False)  # HR_PARTNER, MANAGER, SYSTEM_ADMIN, etc.
    old_state = Column(Text, nullable=True)
    new_state = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_entity", "entity_name", "entity_id"),
        Index("idx_audit_time", "timestamp"),
    )


class ExchangeRate(Base):
    """Effective-dated currency conversion multipliers relative to USD."""
    __tablename__ = "exchange_rates"

    exchange_rate_id = Column(String(32), primary_key=True)  # FX-GBP-USD-2026
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False, default="USD")
    rate = Column(Float, nullable=False)
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("rate > 0", name="chk_rate_pos"),
        Index("idx_fx_lookup", "from_currency", "to_currency", "effective_start_date", "effective_end_date"),
    )


class RoleComparabilityRationale(Base):
    """Bridge table documenting cross-role comparability."""
    __tablename__ = "role_comparability_rationales"

    mapping_id = Column(String(64), primary_key=True)  # RCR-ROLE-A-ROLE-B
    role_id_a = Column(String(32), ForeignKey("roles.role_id", ondelete="CASCADE"), nullable=False)
    role_id_b = Column(String(32), ForeignKey("roles.role_id", ondelete="CASCADE"), nullable=False)
    is_comparable = Column(Boolean, nullable=False, default=True)
    documented_rationale = Column(Text, nullable=False)
    approved_by = Column(String(64), nullable=False)
    effective_date = Column(Date, nullable=False)


class GroundTruthRecord(Base):
    """Isolated ground-truth repository storing known anomalies and expected outcomes."""
    __tablename__ = "ground_truth_records"

    ground_truth_id = Column(String(64), primary_key=True)  # GT-000001
    record_type = Column(String(32), nullable=False)  # EMPLOYEE, SALARY_RECORD, etc.
    record_id = Column(String(128), nullable=False)
    issue_type = Column(String(64), nullable=False)  # EXPIRED_BAND_COMPARISON, etc.
    is_anomaly = Column(Boolean, nullable=False, default=True)
    expected_detection = Column(String(64), nullable=False)
    root_cause_explanation = Column(Text, nullable=False)
    injected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_gt_issue", "issue_type"),
        Index("idx_gt_record", "record_type", "record_id"),
    )
