"""
Multi-Factor Compensation Disparity Detection Engine.
Evaluates normalized employee compensation against peer cohorts, bands, and documented merit factors.
Categorizes outcomes into:
- EXPLAINED_VARIATION
- UNEXPLAINED_DISPARITY
- INVALID_COMPARISON
- INSUFFICIENT_EVIDENCE
- MANUAL_REVIEW_REQUIRED
"""
from typing import Dict, List, Any, Optional
from src.config import (
    COMPA_RATIO_MIN, COMPA_RATIO_MAX,
    DISPARITY_THRESHOLD_PERCENT, PERFORMANCE_EXEMPLARY_RATING
)
from src.engine.compa_ratio import CompaRatioCalculator
from src.engine.within_band import WithinBandCalculator


class DisparityDetectionResult:
    """Encapsulates the comprehensive evaluation for an individual employee."""
    def __init__(
        self,
        employee_id: str,
        status: str,
        compa_ratio: float,
        within_band_position: float,
        deviation_from_cohort_median_pct: float,
        cohort_size: int,
        primary_reason: str,
        supporting_evidence: Dict[str, Any],
        is_disparity: bool = False,
        confidence_score: float = 1.0
    ):
        self.employee_id = employee_id
        self.status = status
        self.compa_ratio = compa_ratio
        self.within_band_position = within_band_position
        self.deviation_from_cohort_median_pct = deviation_from_cohort_median_pct
        self.cohort_size = cohort_size
        self.primary_reason = primary_reason
        self.supporting_evidence = supporting_evidence
        self.is_disparity = is_disparity
        self.confidence_score = confidence_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "status": self.status,
            "compa_ratio": self.compa_ratio,
            "within_band_position": self.within_band_position,
            "deviation_from_cohort_median_pct": self.deviation_from_cohort_median_pct,
            "cohort_size": self.cohort_size,
            "primary_reason": self.primary_reason,
            "supporting_evidence": self.supporting_evidence,
            "is_disparity": self.is_disparity,
            "confidence_score": self.confidence_score
        }


class DisparityDetector:
    """Analyzes compensation distributions across documented job-related factors."""

    def __init__(
        self,
        compa_ratio_min: float = COMPA_RATIO_MIN,
        compa_ratio_max: float = COMPA_RATIO_MAX,
        disparity_threshold_pct: float = DISPARITY_THRESHOLD_PERCENT,
        performance_exemplary_rating: float = PERFORMANCE_EXEMPLARY_RATING,
        min_cohort_size: int = 3
    ):
        self.compa_ratio_min = compa_ratio_min
        self.compa_ratio_max = compa_ratio_max
        self.disparity_threshold_pct = disparity_threshold_pct
        self.performance_exemplary_rating = performance_exemplary_rating
        self.min_cohort_size = min_cohort_size

    def evaluate_employee(
        self,
        employee_id: str,
        normalized_salary: float,
        band_min: float,
        band_mid: float,
        band_max: float,
        cohort_median_salary: float,
        cohort_size: int,
        performance_rating: Optional[float] = None,
        tenure_in_role_years: float = 0.0,
        tenure_in_company_years: float = 0.0,
        promotions_count: int = 0,
        has_pending_adjustment: bool = False,
        has_active_exception: bool = False,
        exception_details: Optional[str] = None
    ) -> DisparityDetectionResult:
        """
        Executes multi-factor disparity evaluation.
        """
        # Step 1: Pre-requisite validation
        if has_active_exception:
            return DisparityDetectionResult(
                employee_id=employee_id,
                status="INVALID_COMPARISON",
                compa_ratio=0.0,
                within_band_position=0.0,
                deviation_from_cohort_median_pct=0.0,
                cohort_size=cohort_size,
                primary_reason=f"Evaluation blocked by operational exception: {exception_details}",
                supporting_evidence={"exception": exception_details},
                is_disparity=False
            )

        if cohort_size < self.min_cohort_size:
            cr = CompaRatioCalculator.calculate(normalized_salary, band_mid)
            wbp = WithinBandCalculator.calculate(normalized_salary, band_min, band_max)
            return DisparityDetectionResult(
                employee_id=employee_id,
                status="INSUFFICIENT_EVIDENCE",
                compa_ratio=cr,
                within_band_position=wbp,
                deviation_from_cohort_median_pct=0.0,
                cohort_size=cohort_size,
                primary_reason=f"Cohort peer size ({cohort_size}) below minimum statistical threshold ({self.min_cohort_size}).",
                supporting_evidence={"cohort_size": cohort_size, "min_required": self.min_cohort_size},
                is_disparity=False
            )

        # Step 2: Compute core metrics
        cr = CompaRatioCalculator.calculate(normalized_salary, band_mid)
        wbp = WithinBandCalculator.calculate(normalized_salary, band_min, band_max)

        dev_from_median_pct = 0.0
        if cohort_median_salary > 0:
            dev_from_median_pct = round(((normalized_salary - cohort_median_salary) / cohort_median_salary) * 100.0, 2)

        evidence = {
            "normalized_salary": normalized_salary,
            "band_min": band_min,
            "band_mid": band_mid,
            "band_max": band_max,
            "compa_ratio": cr,
            "within_band_position": wbp,
            "cohort_median_salary": cohort_median_salary,
            "deviation_from_cohort_median_pct": dev_from_median_pct,
            "performance_rating": performance_rating,
            "tenure_in_company_years": tenure_in_company_years,
            "tenure_in_role_years": tenure_in_role_years,
            "promotions_count": promotions_count,
            "has_pending_adjustment": has_pending_adjustment
        }

        # Step 3: Multi-factor classification rules
        # Condition A: UNEXPLAINED_DISPARITY (Underpaid high performer)
        # Deviation < -15% or CR < 0.80, while performance >= 3.5 and tenure >= 1.0 yr without pending adjustment
        is_underpaid = (dev_from_median_pct < -self.disparity_threshold_pct) or (cr < self.compa_ratio_min)
        is_high_performer = (performance_rating is not None and performance_rating >= self.performance_exemplary_rating)
        is_established_tenure = tenure_in_company_years >= 1.0

        if is_underpaid and is_high_performer and is_established_tenure and not has_pending_adjustment:
            reason = (
                f"Significant negative deviation ({dev_from_median_pct}% vs median, CR: {cr}) "
                f"unexplained by strong performance (rating {performance_rating}/5.0) and established tenure ({tenure_in_company_years:.1f} yrs)."
            )
            return DisparityDetectionResult(
                employee_id=employee_id,
                status="UNEXPLAINED_DISPARITY",
                compa_ratio=cr,
                within_band_position=wbp,
                deviation_from_cohort_median_pct=dev_from_median_pct,
                cohort_size=cohort_size,
                primary_reason=reason,
                supporting_evidence=evidence,
                is_disparity=True,
                confidence_score=0.95
            )

        # Condition B: MANUAL_REVIEW_REQUIRED
        # Outlier deviation (> ±25%) with mixed signals (e.g. low performance but high salary, or high tenure without review)
        if abs(dev_from_median_pct) > 25.0:
            if performance_rating is None:
                return DisparityDetectionResult(
                    employee_id=employee_id,
                    status="MANUAL_REVIEW_REQUIRED",
                    compa_ratio=cr,
                    within_band_position=wbp,
                    deviation_from_cohort_median_pct=dev_from_median_pct,
                    cohort_size=cohort_size,
                    primary_reason="Extreme deviation (> 25%) with missing performance evaluation history.",
                    supporting_evidence=evidence,
                    is_disparity=False
                )
            if dev_from_median_pct > 25.0 and performance_rating < 3.0:
                return DisparityDetectionResult(
                    employee_id=employee_id,
                    status="MANUAL_REVIEW_REQUIRED",
                    compa_ratio=cr,
                    within_band_position=wbp,
                    deviation_from_cohort_median_pct=dev_from_median_pct,
                    cohort_size=cohort_size,
                    primary_reason=f"High positive deviation (+{dev_from_median_pct}%) despite sub-target performance rating ({performance_rating}).",
                    supporting_evidence=evidence,
                    is_disparity=False
                )

        # Condition C: EXPLAINED_VARIATION
        # Difference is well explained by tenure, performance, or recent hire
        explanation = []
        if tenure_in_company_years < 1.0:
            explanation.append("recent hire (tenure < 1 yr)")
        if performance_rating is not None:
            if performance_rating < 3.0:
                explanation.append("developmental performance rating")
            elif performance_rating >= 4.0:
                explanation.append("top-tier performance merit")
        if promotions_count > 0:
            explanation.append("recent promotion adjustment")
        if not explanation:
            explanation.append("compensation aligned with market band and cohort median")

        return DisparityDetectionResult(
            employee_id=employee_id,
            status="EXPLAINED_VARIATION",
            compa_ratio=cr,
            within_band_position=wbp,
            deviation_from_cohort_median_pct=dev_from_median_pct,
            cohort_size=cohort_size,
            primary_reason=f"Compensation variation explained by {', '.join(explanation)}.",
            supporting_evidence=evidence,
            is_disparity=False
        )
