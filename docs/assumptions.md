# Assumptions and Operational Parameters

## 1. Scope & Privacy Assumptions
1. **No Sensitive Demographic Attributes**: In accordance with the prompt guidelines, no protected personal characteristics (gender, race, age, religion, disability) are included in the synthetic employee records or used in decision rules. Disparity analysis is strictly grounded in job-related criteria: role, level, location, documented performance ratings, tenure, promotion history, and compensation bands.
2. **Correlation vs. Causation**: Statistical compensation disparity indicates an anomaly requiring review; it does not in itself constitute legal proof of unlawful discrimination.

## 2. Temporal & Economic Assumptions
1. **Temporal Horizon**: Synthetic data spans a 3-year historical evaluation window (2024 through 2026).
2. **Effective Dates**:
   - Compensation bands are reviewed annually and remain effective from January 1 to December 31 of each calendar year.
   - Foreign exchange rates are effective-dated per calendar year, reflecting annual normalized benchmark rates.
   - Base reporting currency is USD ($).
3. **Pay Frequency & FTE**:
   - Salaried employees have an annual pay frequency; part-time employees have fractional FTE between 0.2 and 0.8.
   - FTE normalization converts partial-time earnings into a 1.0 FTE annualized equivalent to permit fair comparison against full-time peers.

## 3. Organizational Hierarchy Assumptions
1. **Career Ladders**: Standard career progression spans 6 professional levels: L1 (Associate) to L6 (Principal/Director).
2. **Job Families & Functions**: Roles belong to defined job families (Engineering, Data & AI, Product, Design, Operations, Finance, Human Resources). Peer grouping defaults to exact `(role_id, level_id, location_id)` tuples unless a formal role comparability rationale bridges related roles.
3. **Primary Actors**:
   - `EMPLOYEE`: Subject of compensation and career trajectory.
   - `MANAGER`: Recommends adjustments, provides performance evaluations.
   - `HR_PARTNER`: Initiates adjustment proposals, audits equity.
   - `IT_OPS`: Manages data imports and integrations.
   - `SYSTEM_ADMIN`: Enforces compliance rules, system settings, and audit log integrity.

## 4. Reproducibility & Seed
1. **Deterministic Pseudorandom Seed**: Fixed random seed is `20261022`.
2. **Scale Parameters**:
   - `starter`: 100 employees, ~30 role/level combinations, 3-year history for swift local testing.
   - `full`: 5,000 employees, 200 role/level combinations, 3-year history for full benchmark scale.
