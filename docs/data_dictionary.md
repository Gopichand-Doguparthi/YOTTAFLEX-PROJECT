# Comprehensive Data Dictionary

## Overview
This document specifies the exact technical and business data dictionary for the Compensation Equity and Disparity Analysis System. Every field includes data type, optionality, allowed values, units, uniqueness constraints, and validation rules.

---

### 1. Employee (`employees`)
Primary entity representing individual workforce members.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `employee_id` | String(32) | Yes | Regex: `^EMP-[0-9]{6}$` | N/A | Primary Key | Must be formatted as zero-padded 6 digits prefixed with `EMP-`. |
| `first_name` | String(64) | Yes | Non-empty string | N/A | No | Alphabetic text, length between 1 and 64 characters. |
| `last_name` | String(64) | Yes | Non-empty string | N/A | No | Alphabetic text, length between 1 and 64 characters. |
| `email` | String(128) | Yes | Valid email format | N/A | Unique | Standard RFC 5322 email syntax. |
| `department` | String(64) | Yes | Engineering, Data & AI, Product, Sales, Operations, Finance, Human Resources, Legal | N/A | No | Must be one of approved corporate departments. |
| `current_role_id` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | Must reference an existing active Role. |
| `current_level_id` | String(32) | Yes | Foreign Key -> `levels.level_id` | N/A | No | Must reference an existing active Level. |
| `current_location_id` | String(32) | Yes | Foreign Key -> `locations.location_id` | N/A | No | Must reference an existing active Location. |
| `hire_date` | Date | Yes | `YYYY-MM-DD` | Calendar Date | No | Must be <= current date, >= 1990-01-01. |
| `employment_type` | String(20) | Yes | `FULL_TIME`, `PART_TIME`, `CONTRACT` | N/A | No | Must match standard employment classification enum. |
| `fte` | Float | Yes | Range: `(0.0, 1.0]` | Fraction | No | Must be greater than 0 and less than or equal to 1.0. |
| `is_active` | Boolean | Yes | `True`, `False` | N/A | No | Inactive employees excluded from active band reviews. |
| `created_at` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Defaults to record generation timestamp. |
| `updated_at` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Updated upon any field modification. |

---

### 2. Role (`roles`)
Job profiles categorized by job family and function.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `role_id` | String(32) | Yes | `ROLE-<CODE>` (e.g. `ROLE-SWE`) | N/A | Primary Key | Immutable code identifier. |
| `role_title` | String(128) | Yes | Non-empty string | N/A | Unique | Descriptive professional job title. |
| `job_family` | String(64) | Yes | `Engineering`, `Data & AI`, `Product`, `Design`, `Operations`, `Finance`, `HR` | N/A | No | High-level organizational capability family. |
| `job_function` | String(64) | Yes | Specific sub-function | N/A | No | Functional domain classification. |
| `is_active` | Boolean | Yes | `True`, `False` | N/A | No | Indicates active status. |

---

### 3. Level (`levels`)
Standardized professional career ladder hierarchy.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `level_id` | String(16) | Yes | `LVL-L1` through `LVL-L6`, `LVL-EXEC` | N/A | Primary Key | Standard career ladder code. |
| `level_code` | String(16) | Yes | `L1`, `L2`, `L3`, `L4`, `L5`, `L6`, `EXEC` | N/A | Unique | Short mnemonic code. |
| `level_name` | String(64) | Yes | `Associate`, `Mid-Level`, `Senior`, `Staff`, `Principal`, `Director`, `Executive` | N/A | No | Professional career tier title. |
| `rank` | Integer | Yes | 1 to 7 | Ordinal Rank | Unique | Rank order where L1=1, L2=2, etc. Ensures monotonic seniority checks. |

---

### 4. Location (`locations`)
Geographical entities governing local compensation markets, currencies, and cost-of-living.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `location_id` | String(16) | Yes | `LOC-<CODE>` (e.g. `LOC-NYC`, `LOC-LON`) | N/A | Primary Key | Unique geographic identifier. |
| `location_name` | String(128) | Yes | City, Country format | N/A | Unique | Human-readable location description. |
| `country` | String(3) | Yes | ISO 3166-1 alpha-3 (USA, GBR, IND, DEU, JPN, SGP) | N/A | No | 3-letter uppercase country code. |
| `currency` | String(3) | Yes | ISO 4217 (USD, GBP, INR, EUR, JPY, SGD) | Currency Code | No | Local operating currency. |
| `geo_tier` | String(16) | Yes | `Tier-1`, `Tier-2`, `Tier-3` | Market Tier | No | Market compensation adjustment tier. |
| `cost_of_living_index` | Float | Yes | 0.20 to 2.50 | Ratio relative to baseline NYC (1.0) | No | Must be > 0. |

---

### 5. CompensationBand (`compensation_bands`)
Effective-dated salary ranges establishing minimum, midpoint, and maximum bounds for a role/level/location profile.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `band_id` | String(128) | Yes | `BAND-<role>-<level>-<location>-<year>` | N/A | Primary Key | Deterministic compound format. |
| `role_id` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | Valid foreign key. |
| `level_id` | String(16) | Yes | Foreign Key -> `levels.level_id` | N/A | No | Valid foreign key. |
| `location_id` | String(16) | Yes | Foreign Key -> `locations.location_id` | N/A | No | Valid foreign key. |
| `currency` | String(3) | Yes | Matches location currency (ISO 4217) | Currency Code | No | Must match local currency. |
| `min_salary` | Float | Yes | Value > 0 | Local Currency | No | Must be strictly > 0 and < `mid_salary`. |
| `mid_salary` | Float | Yes | Value > `min_salary` | Local Currency | No | Midpoint: `min_salary < mid_salary < max_salary`. |
| `max_salary` | Float | Yes | Value > `mid_salary` | Local Currency | No | Spread: `max_salary > mid_salary`. |
| `effective_start_date`| Date | Yes | `YYYY-MM-DD` | Date | No | Start of band validity window. |
| `effective_end_date`  | Date | No | `YYYY-MM-DD` or NULL | Date | No | If provided, must be >= `effective_start_date`. |
| `status` | String(16) | Yes | `ACTIVE`, `EXPIRED`, `DRAFT` | Lifecycle | No | Must match validity window. |

---

### 6. SalaryRecord (`salary_records`)
Historical and current compensation events for each employee. Preserves immutable compensation history.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `salary_id` | String(64) | Yes | `SAL-<employee-id>-<YYYY>-<MM>` | N/A | Primary Key | Deterministic sequence identifier. |
| `employee_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | No | Valid employee reference. |
| `base_salary` | Float | Yes | Value > 0 | Local Currency | No | Unadjusted local contractual pay. |
| `currency` | String(3) | Yes | ISO 4217 | Currency Code | No | Local currency. |
| `fte` | Float | Yes | Range `(0.0, 1.0]` | Ratio | No | Must match employee's FTE at time of record. |
| `pay_frequency` | String(16) | Yes | `ANNUAL`, `MONTHLY` | Frequency | No | Pay schedule frequency. |
| `normalized_salary` | Float | Yes | Value > 0 | USD (Reporting) | No | Annualized, FX-converted, FTE-normalized salary. |
| `normalized_currency`| String(3) | Yes | `USD` | Reporting Currency | No | Always matches system reporting currency. |
| `effective_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Date when compensation took effect. |
| `end_date` | Date | No | `YYYY-MM-DD` or NULL | Date | No | Superseded date when new compensation applied. |
| `change_reason` | String(32) | Yes | `HIRE`, `ANNUAL_MERIT`, `PROMOTION`, `MARKET_ADJUSTMENT`, `EQUITY_CORRECTION` | Reason Code | No | Documented business rationale for change. |
| `created_at` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Record creation timestamp. |

---

### 7. PerformanceEvidence (`performance_evidence`)
Documented evaluation scores and measurable performance indicators.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `evidence_id` | String(64) | Yes | `PERF-<employee-id>-<cycle>` | N/A | Primary Key | Unique evaluation identifier. |
| `employee_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | No | Valid employee reference. |
| `review_cycle` | String(16) | Yes | e.g. `2023-H2`, `2024-H1`, `2025-H2` | Cycle Code | No | Semi-annual or annual performance cycle. |
| `rating_score` | Float | Yes | 1.0 to 5.0 | Rating Scale | No | 1.0=Unsatisfactory, 3.0=Meets, 4.0=Exceeds, 5.0=Outstanding. |
| `rating_label` | String(32) | Yes | `NEEDS_IMPROVEMENT`, `MEETS_EXPECTATIONS`, `EXCEEDS_EXPECTATIONS`, `OUTSTANDING` | Categorical | No | Must align with numerical `rating_score`. |
| `reviewer_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | No | Evaluating manager/lead. |
| `documented_skills_score`| Float | Yes | 0.0 to 100.0 | Percentile Score | No | Validated assessment score. |
| `critical_initiative_count`| Integer| Yes | >= 0 | Count | No | Number of major deliveries led. |
| `effective_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Review conclusion date. |

---

### 8. Tenure (`tenure_records`)
Tracks organizational and domain experience metrics for each employee.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tenure_id` | String(64) | Yes | `TEN-<employee-id>` | N/A | Primary Key | 1:1 relationship with Employee. |
| `employee_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | Unique | Single active tenure record per employee. |
| `company_start_date`| Date | Yes | `YYYY-MM-DD` | Date | No | Matches employee `hire_date`. |
| `role_start_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Must be >= `company_start_date`. |
| `years_of_experience_total`| Float | Yes | >= 0.0 | Years | No | Total career experience. Must be >= `tenure_in_company_years`. |
| `tenure_in_company_years` | Float | Yes | >= 0.0 | Years | No | Calculated: `(as_of_date - company_start_date) / 365.25`. |
| `tenure_in_role_years` | Float | Yes | >= 0.0 | Years | No | Calculated: `(as_of_date - role_start_date) / 365.25`. |

---

### 9. Promotion (`promotions`)
Tracks historical advancement between career ladder levels or roles.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `promotion_id` | String(64) | Yes | `PROM-<employee-id>-<YYYYMM>` | N/A | Primary Key | Promotion transaction identifier. |
| `employee_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | No | Valid employee reference. |
| `from_level_id` | String(16) | Yes | Foreign Key -> `levels.level_id` | N/A | No | Origin career level. |
| `to_level_id` | String(16) | Yes | Foreign Key -> `levels.level_id` | N/A | No | Destination level (`rank(to) > rank(from)`). |
| `from_role_id` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | Origin role. |
| `to_role_id` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | Destination role. |
| `promotion_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Effective promotion date. |
| `previous_salary` | Float | Yes | Value > 0 | USD Normalized | No | Pre-promotion normalized compensation. |
| `new_salary` | Float | Yes | Value > `previous_salary` | USD Normalized | No | Post-promotion normalized compensation. |
| `increase_percentage` | Float | Yes | Range: `(0.0, 100.0]` | Percentage | No | Calculated: `((new - prev) / prev) * 100`. |
| `approved_by` | String(64) | Yes | Non-empty actor string | N/A | No | Approving authority identifier. |

---

### 10. AdjustmentProposal (`adjustment_proposals`)
Formal compensation remediation proposals addressing identified anomalies and market disparities.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `proposal_id` | String(32) | Yes | Regex: `^ADJ-[0-9]{4}-[0-9]{6}$` (e.g. `ADJ-2026-000001`) | N/A | Primary Key | Strict required ID nomenclature. |
| `employee_id` | String(32) | Yes | Foreign Key -> `employees.employee_id` | N/A | No | Valid employee reference. |
| `current_salary` | Float | Yes | Value > 0 | USD Normalized | No | Current normalized salary. |
| `proposed_salary` | Float | Yes | Value > 0 | USD Normalized | No | Proposed post-adjustment salary. |
| `adjustment_amount` | Float | Yes | `proposed_salary - current_salary` | USD | No | Absolute difference. |
| `adjustment_percentage`| Float | Yes | `(adjustment_amount / current_salary) * 100` | Percentage | No | Relative change percentage. |
| `reason_code` | String(32) | Yes | `INTERNAL_EQUITY`, `MARKET_PARITY`, `DISPARITY_CORRECTION`, `PROMOTION_CATCHUP`, `RETENTION` | Reason Code | No | Standardized business justification. |
| `justification_notes` | Text | Yes | Non-empty text | N/A | No | Narrative context explaining rationale. |
| `evidence_summary` | Text | Yes | Structured summary / JSON | N/A | No | Includes rating, tenure, band benchmark. |
| `related_disparity_findings`| Text | Yes | Structured summary / JSON | N/A | No | Disparity metrics triggering the proposal. |
| `proposed_effective_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Future or active effective date. |
| `approval_status` | String(20) | Yes | `DRAFT`, `PENDING_REVIEW`, `APPROVED`, `REJECTED` | Status Enum | No | Strict finite state machine lifecycle. |
| `created_by` | String(64) | Yes | Actor ID / Email | N/A | No | Proposing actor. |
| `created_at` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Proposal timestamp. |
| `reviewed_by` | String(64) | No | Actor ID / Email or NULL | N/A | No | Required if status is APPROVED or REJECTED. |
| `reviewed_at` | DateTime | No | ISO 8601 Timestamp or NULL | UTC | No | Required if status is APPROVED or REJECTED. |
| `review_notes` | Text | No | Free text or NULL | N/A | No | Reviewer comments. |

---

### 11. ApprovalEvent (`approval_events`)
Append-only audit ledger recording lifecycle transitions and critical compensation events.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | String(64) | Yes | `EVT-<YYYYMMDD>-<sequence>` | N/A | Primary Key | Chronological sequence ID. |
| `entity_name` | String(32) | Yes | `AdjustmentProposal`, `SalaryRecord`, `CompensationBand` | Entity Name | No | Target entity table. |
| `entity_id` | String(128) | Yes | Target entity primary key | N/A | No | Reference to changed entity. |
| `event_type` | String(32) | Yes | `CREATED`, `SUBMITTED_FOR_REVIEW`, `APPROVED`, `REJECTED`, `SALARY_APPLIED`, `EXCEPTION_FLAGGED` | Event Type | No | Validated event taxonomy. |
| `actor_id` | String(64) | Yes | Actor identifier | N/A | No | Identity executing the state change. |
| `actor_role` | String(32) | Yes | `EMPLOYEE`, `MANAGER`, `HR_PARTNER`, `IT_OPS`, `SYSTEM_ADMIN` | Actor Role | No | Must be one of five primary system actors. |
| `old_state` | Text | No | JSON string / state snapshot | N/A | No | Previous entity state. |
| `new_state` | Text | Yes | JSON string / state snapshot | N/A | No | New entity state after transition. |
| `notes` | Text | No | Contextual text | N/A | No | Audit commentary. |
| `timestamp` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Monotonically recorded timestamp. |

---

### 12. ExchangeRate (`exchange_rates`)
Master foreign exchange table for effective-dated currency normalization.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exchange_rate_id` | String(32) | Yes | `FX-<FROM>-<TO>-<YYYY>` | N/A | Primary Key | Compound currency key. |
| `from_currency` | String(3) | Yes | ISO 4217 (USD, GBP, EUR, INR, JPY, SGD) | Currency Code | No | Local currency. |
| `to_currency` | String(3) | Yes | `USD` | Reporting Currency | No | Common reporting standard. |
| `rate` | Float | Yes | Value > 0.0 | Multiplier | No | Exchange multiplier: `USD = local * rate`. |
| `effective_start_date`| Date | Yes | `YYYY-MM-DD` | Date | No | Start of currency validity window. |
| `effective_end_date` | Date | Yes | `YYYY-MM-DD` | Date | No | End of currency validity window. |

---

### 13. RoleComparabilityRationale (`role_comparability_rationales`)
Documented mapping establishing or denying comparability between roles.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mapping_id` | String(64) | Yes | `RCR-<roleA>-<roleB>` | N/A | Primary Key | Compound role pair identifier. |
| `role_id_a` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | First role. |
| `role_id_b` | String(32) | Yes | Foreign Key -> `roles.role_id` | N/A | No | Second role. |
| `is_comparable` | Boolean | Yes | `True`, `False` | N/A | No | Explicit comparability determination. |
| `documented_rationale`| Text | Yes | Required narrative explanation | N/A | No | Must not be empty. |
| `approved_by` | String(64) | Yes | Authority ID | N/A | No | HR or Committee approver. |
| `effective_date` | Date | Yes | `YYYY-MM-DD` | Date | No | Date rationale established. |

---

### 14. GroundTruthRecord (`ground_truth_records`)
Isolated ground-truth repository holding known edge-case anomalies and baseline validation labels.

| Field Name | Data Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ground_truth_id` | String(64) | Yes | `GT-<sequence>` | N/A | Primary Key | Unique ground truth record ID. |
| `record_type` | String(32) | Yes | `EMPLOYEE`, `SALARY_RECORD`, `COMPENSATION_BAND`, `ADJUSTMENT_PROPOSAL`, `COMPARABLE_GROUP` | Record Type | No | Target entity domain. |
| `record_id` | String(128) | Yes | Target entity primary key | N/A | No | Reference to subject record. |
| `issue_type` | String(64) | Yes | `EXPIRED_BAND_COMPARISON`, `FTE_IGNORED_IN_NORMALIZATION`, `MISSING_CURRENCY_CONVERSION`, `UNAPPROVED_ADJUSTMENT_APPLIED`, `INCOMPARABLE_ROLE_GROUPING`, `UNEXPLAINED_DISPARITY_LOW`, `UNEXPLAINED_DISPARITY_HIGH`, `VALID_BASELINE` | Issue Type Enum | No | Strict ground truth issue classification. |
| `is_anomaly` | Boolean | Yes | `True` for edge cases / disparities; `False` for valid baselines | N/A | No | Binary anomaly label. |
| `expected_detection` | String(64) | Yes | Expected engine detection outcome | N/A | No | e.g. `EXCEPTION_FLAGGED`, `DISPARITY_DETECTED`, `VALID`. |
| `root_cause_explanation`| Text | Yes | Detailed factual explanation | N/A | No | Contextual evidence and rationale. |
| `injected_at` | DateTime | Yes | ISO 8601 Timestamp | UTC | No | Injected timestamp. |
