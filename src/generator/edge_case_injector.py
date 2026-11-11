"""
Edge Case and Anomaly Injection Module.
Injects the Five Mandatory Edge Cases and Deliberate Disparities into synthetic datasets.
Produces isolated ground-truth records with detailed root cause explanations.
"""
from datetime import date, datetime
from typing import Dict, List, Any, Tuple
from src.generator.seed_data import EXCHANGE_RATES_SEED


class EdgeCaseInjector:
    """Injects specific labeled edge cases into baseline datasets."""

    @staticmethod
    def inject_edge_cases(
        employees: List[Dict[str, Any]],
        salary_records: List[Dict[str, Any]],
        compensation_bands: List[Dict[str, Any]],
        proposals: List[Dict[str, Any]],
        approval_events: List[Dict[str, Any]],
        performances: List[Dict[str, Any]],
        role_rationales: List[Dict[str, Any]],
        num_anomalies_each: int = 5
    ) -> Tuple[
        List[Dict[str, Any]],  # modified salary records
        List[Dict[str, Any]],  # modified proposals
        List[Dict[str, Any]],  # ground truth records
        List[Dict[str, Any]]   # modified bands / comparability
    ]:
        ground_truth: List[Dict[str, Any]] = []
        gt_counter = 0

        emp_lookup = {e["employee_id"]: e for e in employees}

        # Build FX lookup
        fx_lookup = {}
        for fx in EXCHANGE_RATES_SEED:
            yr = int(fx["effective_start_date"][:4])
            fx_lookup[(fx["from_currency"], yr)] = fx["rate"]

        def add_gt(record_type: str, record_id: str, issue_type: str, expected_detection: str, explanation: str):
            nonlocal gt_counter
            gt_counter += 1
            ground_truth.append({
                "ground_truth_id": f"GT-{gt_counter:06d}",
                "record_type": record_type,
                "record_id": record_id,
                "issue_type": issue_type,
                "is_anomaly": True,
                "expected_detection": expected_detection,
                "root_cause_explanation": explanation,
                "injected_at": "2026-01-01T00:00:00"
            })

        # -------------------------------------------------------------
        # 1. MANDATORY EDGE CASE 1: Salary compared against expired band
        # -------------------------------------------------------------
        count_ec1 = 0
        for sal in salary_records:
            if sal.get("effective_date", "").startswith("2026") and count_ec1 < num_anomalies_each:
                emp = emp_lookup.get(sal["employee_id"])
                if emp:
                    # Explicitly benchmark against expired 2024 band
                    expired_band_id = f"BAND-{emp['current_role_id']}-{emp['current_level_id']}-{emp['current_location_id']}-2024"
                    sal["benchmark_band_id"] = expired_band_id
                    add_gt(
                        record_type="SALARY_RECORD",
                        record_id=sal["salary_id"],
                        issue_type="EXPIRED_BAND_COMPARISON",
                        expected_detection="EXCEPTION_FLAGGED",
                        explanation=f"Salary {sal['salary_id']} (effective {sal['effective_date']}) benchmarked against expired band {expired_band_id} (expired 2024-12-31)."
                    )
                    count_ec1 += 1

        # -------------------------------------------------------------
        # 2. MANDATORY EDGE CASE 2: FTE ignored during normalization
        # -------------------------------------------------------------
        count_ec2 = 0
        for emp in employees:
            if emp["employment_type"] == "PART_TIME" and emp["fte"] < 1.0 and count_ec2 < num_anomalies_each:
                emp_id = emp["employee_id"]
                emp_sals = [s for s in salary_records if s["employee_id"] == emp_id]
                if emp_sals:
                    target_sal = emp_sals[-1]
                    eff_yr = int(target_sal["effective_date"][:4])
                    fx_rate = fx_lookup.get((target_sal["currency"], eff_yr), 1.0)
                    annual_base = target_sal["base_salary"]  # ANNUAL
                    # Unadjusted USD without dividing by FTE:
                    unadjusted_usd = round(annual_base * fx_rate, 2)
                    target_sal["normalized_salary"] = unadjusted_usd
                    add_gt(
                        record_type="SALARY_RECORD",
                        record_id=target_sal["salary_id"],
                        issue_type="FTE_IGNORED_IN_NORMALIZATION",
                        expected_detection="EXCEPTION_FLAGGED",
                        explanation=f"Part-time employee {emp_id} (FTE {emp['fte']}) salary not divided by FTE; normalized salary left as {unadjusted_usd} USD instead of {round(unadjusted_usd/emp['fte'], 2)} USD."
                    )
                    count_ec2 += 1

        # -------------------------------------------------------------
        # 3. MANDATORY EDGE CASE 3: Currency conversion missing
        # -------------------------------------------------------------
        count_ec3 = 0
        for sal in salary_records:
            if sal["currency"] in ["INR", "JPY"] and count_ec3 < num_anomalies_each:
                sal["normalized_salary"] = round(sal["base_salary"], 2)  # 1:1 bug
                add_gt(
                    record_type="SALARY_RECORD",
                    record_id=sal["salary_id"],
                    issue_type="MISSING_CURRENCY_CONVERSION",
                    expected_detection="EXCEPTION_FLAGGED",
                    explanation=f"Salary {sal['salary_id']} paid in {sal['currency']} was treated 1:1 without FX conversion, yielding incorrect normalized salary of {sal['normalized_salary']} USD."
                )
                count_ec3 += 1

        # -------------------------------------------------------------
        # 4. MANDATORY EDGE CASE 4: Adjustment applied without approval
        # -------------------------------------------------------------
        count_ec4 = 0
        for prop in proposals:
            if prop["approval_status"] in ["REJECTED", "DRAFT"] and count_ec4 < num_anomalies_each:
                emp_id = prop["employee_id"]
                rogue_sal_id = f"SAL-{emp_id}-2026-99"
                rogue_record = {
                    "salary_id": rogue_sal_id,
                    "employee_id": emp_id,
                    "base_salary": prop["proposed_salary"],
                    "currency": "USD",
                    "fte": 1.0,
                    "pay_frequency": "ANNUAL",
                    "normalized_salary": prop["proposed_salary"],
                    "normalized_currency": "USD",
                    "effective_date": "2026-06-01",
                    "end_date": None,
                    "change_reason": "EQUITY_CORRECTION",
                    "benchmark_band_id": None,
                    "created_at": "2026-06-01T09:00:00"
                }
                salary_records.append(rogue_record)
                add_gt(
                    record_type="SALARY_RECORD",
                    record_id=rogue_sal_id,
                    issue_type="UNAPPROVED_ADJUSTMENT_APPLIED",
                    expected_detection="EXCEPTION_FLAGGED",
                    explanation=f"Salary record {rogue_sal_id} applied equity correction of {prop['proposed_salary']} despite proposal {prop['proposal_id']} having status {prop['approval_status']} with no approval event."
                )
                count_ec4 += 1

        # -------------------------------------------------------------
        # 5. MANDATORY EDGE CASE 5: Incomparable roles grouped without rationale
        # -------------------------------------------------------------
        count_ec5 = 0
        incomparable_pairs = [("ROLE-SWE", "ROLE-FAC"), ("ROLE-DS", "ROLE-LOG"), ("ROLE-PM", "ROLE-REC")]
        for role_a, role_b in incomparable_pairs:
            if count_ec5 < num_anomalies_each:
                add_gt(
                    record_type="COMPARABLE_GROUP",
                    record_id=f"GRP-{role_a}-{role_b}",
                    issue_type="INCOMPARABLE_ROLE_GROUPING",
                    expected_detection="EXCEPTION_FLAGGED",
                    explanation=f"Roles {role_a} and {role_b} grouped together without documented comparability rationale."
                )
                count_ec5 += 1

        # -------------------------------------------------------------
        # 6. DELIBERATE UNEXPLAINED DISPARITIES (Low)
        # -------------------------------------------------------------
        # Count cohort sizes to only pick employees in cohorts with size >= 4
        cohort_counts = {}
        for emp in employees:
            key = f"{emp['current_role_id']}::{emp['current_level_id']}::{emp['current_location_id']}"
            cohort_counts[key] = cohort_counts.get(key, 0) + 1

        count_disp = 0
        for emp in employees:
            key = f"{emp['current_role_id']}::{emp['current_level_id']}::{emp['current_location_id']}"
            if emp["employment_type"] == "FULL_TIME" and cohort_counts.get(key, 0) >= 4 and count_disp < (num_anomalies_each * 2):
                emp_id = emp["employee_id"]
                emp_sals = [s for s in salary_records if s["employee_id"] == emp_id and s["effective_date"].startswith("2026")]
                emp_perfs = [p for p in performances if p["employee_id"] == emp_id]
                if emp_sals and emp_perfs:
                    # Give outstanding performance
                    for p in emp_perfs:
                        p["rating_score"] = 4.8
                        p["rating_label"] = "OUTSTANDING"

                    target_sal = emp_sals[-1]
                    # Cut normalized salary by 35% below band midpoint
                    target_sal["normalized_salary"] = round(target_sal["normalized_salary"] * 0.65, 2)
                    target_sal["base_salary"] = target_sal["normalized_salary"]

                    add_gt(
                        record_type="EMPLOYEE",
                        record_id=emp_id,
                        issue_type="UNEXPLAINED_DISPARITY_LOW",
                        expected_detection="DISPARITY_DETECTED",
                        explanation=f"Employee {emp_id} has outstanding rating (4.8) but salary depressed to {target_sal['normalized_salary']} USD (>25% below cohort median)."
                    )
                    count_disp += 1

        return salary_records, proposals, ground_truth, compensation_bands
