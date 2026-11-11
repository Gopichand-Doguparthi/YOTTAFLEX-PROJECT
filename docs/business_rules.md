# Compensation Business Rules & Logic Specifications

## 1. Currency Normalization
All compensation is benchmarked against a standardized reporting currency (default: `USD`).
- **Formula**:
  $$\text{Converted Base Salary} = \text{Local Base Salary} \times \text{Exchange Rate}(currency \to USD, \text{effective\_date})$$
- **Rule 1.1**: The exchange rate is resolved from `exchange_rates` where:
  $$\text{effective\_start\_date} \le \text{salary.effective\_date} \le \text{effective\_end\_date}$$
- **Rule 1.2 (Mandatory Edge Case 3)**: If a matching exchange rate does NOT exist for the currency and effective date, the record MUST be flagged with exception `MISSING_CURRENCY_CONVERSION`. Under no circumstances should an arbitrary or default 1.0 rate be silently assumed.

## 2. FTE Normalization
Part-time employees receive pay proportional to their working fraction (`fte`). To make compensation comparable across peers, base pay must be annualized to a 1.0 Full-Time Equivalent (FTE).
- **Formula**:
  $$\text{Normalized Annual Salary} = \frac{\text{Annualized Converted Base Salary}}{\text{fte}}$$
- **Rule 2.1**: If `pay_frequency == 'MONTHLY'`, the annualized base salary is $\text{base\_salary} \times 12$. If `ANNUAL`, it is $\text{base\_salary}$.
- **Rule 2.2 (Mandatory Edge Case 2)**: When calculating band comparisons or cohort medians, un-normalized part-time salaries must never be compared directly against full-time benchmarks. Any comparison where FTE is ignored must be flagged with `FTE_IGNORED_IN_NORMALIZATION`.

## 3. Compa-Ratio Calculation
Compa-ratio quantifies how an employee's normalized compensation benchmarks against the competitive market midpoint for their exact role, level, and location.
- **Formula**:
  $$\text{Compa-Ratio} = \frac{\text{Normalized Employee Salary}}{\text{Applicable Band Midpoint}}$$
- **Target Range**: Standard organizational healthy target range is $0.80 \le \text{Compa-Ratio} \le 1.20$.
  - Compa-ratio $< 0.80$: Under-benchmark (requires equity review).
  - $0.80 \le \text{Compa-Ratio} \le 1.20$: Within target range.
  - Compa-ratio $> 1.20$: Above benchmark (premium tier or red-circle risk).

## 4. Within-Band Position Calculation
Within-Band Position evaluates where the employee's compensation falls along the range between the band minimum and band maximum.
- **Formula**:
  $$\text{Within-Band Position} = \frac{\text{Normalized Salary} - \text{Band Minimum}}{\text{Band Maximum} - \text{Band Minimum}}$$
- **Interpretation**:
  - $< 0.0$: Below band minimum (Green-circled).
  - $0.0 \le \text{Position} \le 0.25$: Lower quartile (Entry / early in level).
  - $0.25 < \text{Position} \le 0.75$: Mid range (Proficient / core performer).
  - $0.75 < \text{Position} \le 1.0$: Upper quartile (Expert / high performer).
  - $> 1.0$: Above band maximum (Red-circled).

## 5. Band Validity Window (Mandatory Edge Case 1)
- **Rule 5.1**: An employee's salary record effective at date $D$ must ONLY be evaluated against a compensation band where:
  $$\text{band.effective\_start\_date} \le D \le \text{band.effective\_end\_date}$$
- **Rule 5.2 (Mandatory Edge Case 1)**: If a salary is evaluated against a band whose `effective_end_date` is strictly prior to the salary effective date, the engine flags `EXPIRED_BAND_COMPARISON`.

## 6. Comparable Group Formation & Rationale (Mandatory Edge Case 5)
Comparable groups (peer cohorts) consist of employees who perform substantially similar work under similar working conditions.
- **Base Cohort Key**: `(role_id, level_id, location_id)`.
- **Cross-Role Grouping**: Two distinct roles may only be grouped together into a comparable cohort if an active entry exists in `role_comparability_rationales` with `is_comparable == True` and a non-empty `documented_rationale`.
- **Rule 6.1 (Mandatory Edge Case 5)**: If disparate roles are grouped without an approved comparability rationale, the system raises `INCOMPARABLE_ROLE_GROUPING`.
- **Minimum Cohort Size**: If a peer group has fewer than 3 employees, cohort-relative statistics are marked `INSUFFICIENT_EVIDENCE`.

## 7. Multi-Factor Disparity Detection Logic
Disparity detection examines the relationship between an employee's compensation relative to peers and documented performance/tenure factors:
- **Cohort Median Compa-Ratio**: $\text{Median}(\text{Compa-Ratio}_{\text{cohort}})$.
- **Cohort Deviation**:
  $$\Delta_{\text{cohort}} = \frac{\text{Employee Compa-Ratio} - \text{Median Compa-Ratio}_{\text{cohort}}}{\text{Median Compa-Ratio}_{\text{cohort}}} \times 100\%$$
- **Classification Rules**:
  1. **`UNEXPLAINED_DISPARITY`**:
     - $\Delta_{\text{cohort}} < -15.0\%$ (or Compa-Ratio $< 0.80$), AND
     - Documented performance is high (`rating_score >= 3.5` or `EXCEEDS_EXPECTATIONS` / `OUTSTANDING`), AND
     - Company tenure $\ge 1.0$ year, AND
     - No approved pending or active equity adjustment exists.
  2. **`EXPLAINED_VARIATION`**:
     - Lower compensation aligned with lower tenure ($< 1$ yr) or developmental rating (`rating_score < 3.0`).
     - Higher compensation aligned with high tenure ($> 5$ yrs), exemplary rating, or specialized skill score.
  3. **`INVALID_COMPARISON`**:
     - Associated with any of the 5 mandatory edge-case exceptions.
  4. **`INSUFFICIENT_EVIDENCE`**:
     - Cohort size $< 3$, or performance review records missing.
  5. **`MANUAL_REVIEW_REQUIRED`**:
     - Outliers outside $\pm 25\%$ of cohort median where conflicting performance or promotion signals exist.

## 8. Adjustment Proposal & Approval Lifecycle (Mandatory Edge Case 4)
- **State Machine**:
  $$\text{DRAFT} \longrightarrow \text{PENDING\_REVIEW} \longrightarrow \{\text{APPROVED}, \text{REJECTED}\}$$
- **Rule 8.1**: A proposed salary adjustment must be formally reviewed and approved by an authorized actor (`HR_PARTNER` or `MANAGER`).
- **Rule 8.2 (Mandatory Edge Case 4)**: A salary record may not reflect an equity correction or market adjustment unless a corresponding proposal is in `APPROVED` status with an immutable `ApprovalEvent` logged. If a salary record reflects an unapproved adjustment, the engine flags `UNAPPROVED_ADJUSTMENT_APPLIED`.
- **Rule 8.3**: All status transitions emit an immutable audit event into `approval_events`.
