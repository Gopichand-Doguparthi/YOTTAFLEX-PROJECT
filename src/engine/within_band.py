"""
Within-Band Position Calculation Module.
Within-band position = (Normalized salary - Band minimum) / (Band maximum - Band minimum).
Evaluates employee placement across salary band range.
"""
from typing import Dict, Any


class WithinBandCalculator:
    """Computes within-band positioning and flags range exceptions."""

    @staticmethod
    def calculate(normalized_salary: float, band_min: float, band_max: float) -> float:
        """
        Calculates within-band position.
        Band spread (band_max - band_min) must be strictly positive.
        """
        if band_max <= band_min:
            raise ValueError(f"Band maximum ({band_max}) must be strictly greater than band minimum ({band_min})")
        if band_min <= 0:
            raise ValueError(f"Band minimum must be positive; got {band_min}")

        spread = float(band_max) - float(band_min)
        pos = (float(normalized_salary) - float(band_min)) / spread
        return round(pos, 4)

    @staticmethod
    def classify_zone(position: float) -> str:
        """
        Categorizes within-band positioning:
        - GREEN_CIRCLED: < 0.0 (below band minimum, severe underpayment)
        - LOWER_QUARTILE: 0.0 <= pos <= 0.25 (entry/developing)
        - MID_LOWER: 0.25 < pos <= 0.50 (progressing)
        - MID_UPPER: 0.50 < pos <= 0.75 (proficient)
        - UPPER_QUARTILE: 0.75 < pos <= 1.00 (mastery/high performer)
        - RED_CIRCLED: > 1.00 (above band maximum, compensation ceiling risk)
        """
        if position < 0.0:
            return "GREEN_CIRCLED"
        elif position <= 0.25:
            return "LOWER_QUARTILE"
        elif position <= 0.50:
            return "MID_LOWER"
        elif position <= 0.75:
            return "MID_UPPER"
        elif position <= 1.00:
            return "UPPER_QUARTILE"
        else:
            return "RED_CIRCLED"

    @classmethod
    def analyze(cls, normalized_salary: float, band_min: float, band_max: float) -> Dict[str, Any]:
        """Provides full within-band position metrics."""
        pos = cls.calculate(normalized_salary, band_min, band_max)
        zone = cls.classify_zone(pos)
        is_outside_band = pos < 0.0 or pos > 1.0
        return {
            "within_band_position": pos,
            "within_band_percentage": round(pos * 100.0, 2),
            "zone": zone,
            "is_outside_band": is_outside_band,
            "is_green_circled": pos < 0.0,
            "is_red_circled": pos > 1.0
        }
