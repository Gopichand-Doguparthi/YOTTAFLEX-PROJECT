"""
Full-Time Equivalent (FTE) Normalization Module.
Scales part-time compensation to 1.0 full-time equivalent annual pay.
Prevents double-normalization and detects un-normalized comparisons.
"""
from typing import Optional


class InvalidFTEException(Exception):
    """Raised when an FTE value falls outside the valid (0.0, 1.0] interval."""
    pass


class FTENormalizer:
    """Calculates and validates FTE-adjusted compensation."""

    @staticmethod
    def annualize(base_salary: float, pay_frequency: str = "ANNUAL") -> float:
        """Converts pay to annual base according to frequency."""
        freq = (pay_frequency or "ANNUAL").upper()
        if freq == "ANNUAL":
            return float(base_salary)
        elif freq == "MONTHLY":
            return float(base_salary) * 12.0
        elif freq == "BIWEEKLY":
            return float(base_salary) * 26.0
        elif freq == "WEEKLY":
            return float(base_salary) * 52.0
        else:
            raise ValueError(f"Unsupported pay frequency: {pay_frequency}")

    @classmethod
    def normalize_salary(
        cls,
        base_salary: float,
        fte: float = 1.0,
        pay_frequency: str = "ANNUAL",
        fx_rate: float = 1.0
    ) -> float:
        """
        Normalizes salary:
        1. Annualizes base salary.
        2. Applies foreign exchange multiplier to reporting currency.
        3. Scales to 1.0 FTE by dividing by FTE.
        """
        if fte <= 0.0 or fte > 1.0:
            raise InvalidFTEException(f"FTE must be strictly between 0.0 and 1.0; received {fte}")

        annual_base = cls.annualize(base_salary, pay_frequency)
        annual_usd = annual_base * fx_rate
        # Normalized to 1.0 FTE:
        normalized = annual_usd / fte
        return round(normalized, 2)

    @classmethod
    def is_fte_ignored(
        cls,
        recorded_normalized_salary: float,
        base_salary: float,
        fte: float,
        pay_frequency: str = "ANNUAL",
        fx_rate: float = 1.0,
        tolerance_ratio: float = 0.05
    ) -> bool:
        """
        Detects Mandatory Edge Case 2:
        Checks whether recorded normalized salary was computed WITHOUT dividing by FTE
        (i.e. part-time compensation left unadjusted, comparing a 0.5 FTE salary as if it were full-time).
        """
        if abs(fte - 1.0) < 0.001:
            # Full time employees cannot have FTE ignored error
            return False

        annual_base = cls.annualize(base_salary, pay_frequency)
        unadjusted_usd = annual_base * fx_rate
        expected_normalized = unadjusted_usd / fte

        # If recorded_normalized is close to unadjusted_usd rather than expected_normalized:
        diff_from_unadjusted = abs(recorded_normalized_salary - unadjusted_usd)
        diff_from_expected = abs(recorded_normalized_salary - expected_normalized)

        if diff_from_unadjusted < (unadjusted_usd * tolerance_ratio) and diff_from_expected > (expected_normalized * tolerance_ratio):
            return True
        return False
