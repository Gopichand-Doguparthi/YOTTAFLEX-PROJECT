"""
Compa-Ratio Calculation and Benchmarking Module.
Compa-ratio = Normalized employee salary / Applicable compensation band midpoint.
"""
from typing import Dict, Any


class CompaRatioCalculator:
    """Computes compa-ratios and provides analytical band categorizations."""

    @staticmethod
    def calculate(normalized_salary: float, band_midpoint: float) -> float:
        """
        Calculates compa-ratio.
        Throws ZeroDivisionError or ValueError if band midpoint <= 0.
        """
        if band_midpoint <= 0:
            raise ValueError(f"Compensation band midpoint must be strictly positive; got {band_midpoint}")
        if normalized_salary < 0:
            raise ValueError(f"Normalized salary cannot be negative; got {normalized_salary}")

        return round(float(normalized_salary) / float(band_midpoint), 4)

    @staticmethod
    def classify(compa_ratio: float, min_target: float = 0.80, max_target: float = 1.20) -> str:
        """
        Classifies compa-ratio against corporate guidelines.
        - BELOW_TARGET: < min_target (typically < 0.80)
        - TARGET_RANGE: [min_target, max_target] (typically 0.80 - 1.20)
        - ABOVE_TARGET: > max_target (typically > 1.20)
        """
        if compa_ratio < min_target:
            return "BELOW_TARGET"
        elif compa_ratio > max_target:
            return "ABOVE_TARGET"
        else:
            return "TARGET_RANGE"

    @classmethod
    def analyze(cls, normalized_salary: float, band_midpoint: float, min_target: float = 0.80, max_target: float = 1.20) -> Dict[str, Any]:
        """Returns comprehensive compa-ratio analytics."""
        cr = cls.calculate(normalized_salary, band_midpoint)
        classification = cls.classify(cr, min_target, max_target)
        deviation_pct = round((cr - 1.0) * 100.0, 2)
        return {
            "compa_ratio": cr,
            "classification": classification,
            "deviation_from_midpoint_pct": deviation_pct,
            "is_outlier": cr < min_target or cr > max_target
        }
