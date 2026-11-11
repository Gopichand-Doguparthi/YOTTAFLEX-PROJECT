"""
Comparable Groups and Cohort Analysis Module.
Defines peer cohort structures across role, level, location, and validated cross-role rationales.
Enforces Mandatory Edge Case 5: Incomparable roles grouped without documented rationale.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


class IncomparableRoleGroupingException(Exception):
    """Raised when roles are grouped without documented business comparability rationale."""
    def __init__(self, role_a: str, role_b: str, message: Optional[str] = None):
        self.role_a = role_a
        self.role_b = role_b
        msg = message or f"Mandatory Edge Case 5: Incomparable roles '{role_a}' and '{role_b}' grouped without documented rationale."
        super().__init__(msg)


class ComparableGroupEngine:
    """Manages cohort segmentation, peer comparisons, and cross-role validation."""

    def __init__(self, rationales: Optional[List[Dict]] = None):
        # rationales: list of dicts with keys role_id_a, role_id_b, is_comparable, documented_rationale
        self.rationales = rationales or []

    def load_rationales_from_db(self, session):
        """Loads documented role comparability rationales from the database."""
        from src.database.models import RoleComparabilityRationale
        records = session.query(RoleComparabilityRationale).all()
        self.rationales = [
            {
                "role_id_a": r.role_id_a,
                "role_id_b": r.role_id_b,
                "is_comparable": bool(r.is_comparable),
                "documented_rationale": r.documented_rationale or ""
            }
            for r in records
        ]

    def validate_role_pair_comparability(self, role_a: str, role_b: str) -> Tuple[bool, str]:
        """
        Validates whether role_a and role_b can be legally compared.
        Returns (is_valid, reason).
        """
        if role_a == role_b:
            return True, "Identical role profiles."

        # Search rationale bridge
        for r in self.rationales:
            if (r["role_id_a"] == role_a and r["role_id_b"] == role_b) or \
               (r["role_id_a"] == role_b and r["role_id_b"] == role_a):
                if r["is_comparable"] and len(r["documented_rationale"].strip()) > 0:
                    return True, f"Approved rationale: {r['documented_rationale']}"
                else:
                    return False, f"Documented exclusion: {r['documented_rationale']}"

        return False, f"No documented comparability rationale exists between '{role_a}' and '{role_b}'."

    def build_cohort_key(self, role_id: str, level_id: str, location_id: str) -> str:
        """Constructs standardized cohort key."""
        return f"{role_id}::{level_id}::{location_id}"

    def compute_cohort_statistics(self, records: List[Dict[str, Any]], min_cohort_size: int = 3) -> Dict[str, Dict[str, Any]]:
        """
        Computes summary statistics (count, median, mean, min, max, std) for each peer cohort.
        Flags cohorts below min_cohort_size as INSUFFICIENT_EVIDENCE.
        """
        if not records:
            return {}

        df = pd.DataFrame(records)
        if "cohort_key" not in df.columns:
            df["cohort_key"] = df.apply(
                lambda row: self.build_cohort_key(row["role_id"], row["level_id"], row["location_id"]),
                axis=1
            )

        cohort_stats = {}
        grouped = df.groupby("cohort_key")

        for key, group in grouped:
            count = len(group)
            salaries = group["normalized_salary"].astype(float).values
            roles_in_group = group["role_id"].unique().tolist()

            # Check cross-role comparability if multiple roles present in cohort
            has_incomparable_roles = False
            incomparable_details = []
            if len(roles_in_group) > 1:
                for i in range(len(roles_in_group)):
                    for j in range(i + 1, len(roles_in_group)):
                        valid, reason = self.validate_role_pair_comparability(roles_in_group[i], roles_in_group[j])
                        if not valid:
                            has_incomparable_roles = True
                            incomparable_details.append(reason)

            is_sufficient = count >= min_cohort_size

            cohort_stats[key] = {
                "cohort_key": key,
                "count": count,
                "median_salary": float(np.median(salaries)) if count > 0 else 0.0,
                "mean_salary": float(np.mean(salaries)) if count > 0 else 0.0,
                "min_salary": float(np.min(salaries)) if count > 0 else 0.0,
                "max_salary": float(np.max(salaries)) if count > 0 else 0.0,
                "std_salary": float(np.std(salaries)) if count > 1 else 0.0,
                "is_sufficient": is_sufficient,
                "status": "SUFFICIENT" if is_sufficient else "INSUFFICIENT_EVIDENCE",
                "has_incomparable_roles": has_incomparable_roles,
                "incomparable_details": "; ".join(incomparable_details) if incomparable_details else "Valid cohort grouping."
            }

        return cohort_stats
