# Database Schema & Entity-Relationship Specifications

## 1. Relational Cardinalities & Architecture
The database schema models the complete talent compensation lifecycle with referential integrity, effective-date range boundaries, and audit trail retention.

```
       ┌────────────────────────┐
       │       locations        │
       │  PK: location_id       │
       └───────────┬────────────┘
                   │ 1:N
                   ▼
┌──────────────┐ 1:N ┌─────────────────────┐ 1:N ┌──────────────┐
│    roles     ├────►│ compensation_bands  │◄────┤    levels    │
│ PK: role_id  │     │ PK: band_id         │     │ PK: level_id │
└──────┬───────┘     └─────────────────────┘     └──────┬───────┘
       │ 1:N                                            │ 1:N
       ▼                                                ▼
┌───────────────────────────────────────────────────────────────┐
│                          employees                            │
│  PK: employee_id                                              │
│  FK: current_role_id -> roles.role_id                         │
│  FK: current_level_id -> levels.level_id                       │
│  FK: current_location_id -> locations.location_id             │
└──────┬───────────────┬───────────────┬────────────────┬───────┘
       │ 1:N           │ 1:1           │ 1:N            │ 1:N
       ▼               ▼               ▼                ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│salary_records││tenure_records││  promotions  ││performance_ev│
│PK: salary_id ││PK: tenure_id ││PK: prom_id   ││PK: evidence_id│
└──────────────┘└──────────────┘└──────────────┘└───────┬──────┘
       │ 1:N                                            │
       ▼                                                │
┌──────────────────────────────┐                        │
│     adjustment_proposals     │◄───────────────────────┘
│     PK: proposal_id          │ (referenced in evidence)
└──────────────┬───────────────┘
               │ 1:N
               ▼
┌──────────────────────────────┐
│        approval_events       │
│        PK: event_id          │
└──────────────────────────────┘
```

## 2. Cardinality Matrix
- **Employee to Role**: Many-to-One (N:1). Each employee has one current role; roles have many employees.
- **Employee to Level**: Many-to-One (N:1). Each employee has one current level; levels have many employees.
- **Employee to Location**: Many-to-One (N:1). Each employee has one current location; locations have many employees.
- **CompensationBand to Role, Level, Location**: Many-to-One (N:1 each). Compound uniqueness across `(role_id, level_id, location_id, effective_start_date)`.
- **Employee to SalaryRecord**: One-to-Many (1:N). Preserves historical compensation records over multiple years. Never overwritten.
- **Employee to PerformanceEvidence**: One-to-Many (1:N). Preserves historical performance cycle reviews.
- **Employee to Tenure**: One-to-One (1:1). Single authoritative tenure record per employee.
- **Employee to Promotion**: One-to-Many (1:N). Historical promotional progressions over career.
- **Employee to AdjustmentProposal**: One-to-Many (1:N). Tracks compensation remediation proposals.
- **Role to Role Comparability**: Many-to-Many (N:M). Implemented via bridge table `role_comparability_rationales` with explicit documented rationale.
- **Entity to ApprovalEvent**: One-to-Many (1:N). Polymorphic append-only audit trail capturing lifecycle mutations.

## 3. Referential Integrity & Constraints
1. **Primary Keys**: Every table has an explicit immutable string primary key.
2. **Foreign Keys**: Enforced on all child tables (`ON DELETE RESTRICT`) to preserve auditability.
3. **Check Constraints**:
   - `compensation_bands`: `CHECK (min_salary > 0 AND min_salary < mid_salary AND mid_salary < max_salary)`
   - `salary_records`: `CHECK (base_salary > 0 AND fte > 0 AND fte <= 1.0 AND normalized_salary > 0)`
   - `employees`: `CHECK (fte > 0 AND fte <= 1.0)`
   - `performance_evidence`: `CHECK (rating_score >= 1.0 AND rating_score <= 5.0)`
   - `exchange_rates`: `CHECK (rate > 0)`
   - `levels`: `CHECK (rank >= 1)`
4. **Indexes**:
   - `idx_emp_role_lvl_loc` on `employees(current_role_id, current_level_id, current_location_id)`
   - `idx_sal_emp_eff` on `salary_records(employee_id, effective_date)`
   - `idx_band_lookup` on `compensation_bands(role_id, level_id, location_id, effective_start_date, effective_end_date)`
   - `idx_adj_status` on `adjustment_proposals(approval_status)`
   - `idx_audit_entity` on `approval_events(entity_name, entity_id)`
   - `idx_perf_emp_cycle` on `performance_evidence(employee_id, review_cycle)`
