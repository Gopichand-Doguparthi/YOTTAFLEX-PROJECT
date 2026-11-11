"""
Tests for Compa-Ratio Calculation and Benchmarking.
"""
import pytest
from src.engine.compa_ratio import CompaRatioCalculator


def test_compa_ratio_calculation():
    # 150,000 / 150,000 = 1.00
    assert CompaRatioCalculator.calculate(150000.0, 150000.0) == 1.00

    # 120,000 / 150,000 = 0.80
    assert CompaRatioCalculator.calculate(120000.0, 150000.0) == 0.80

    # 180,000 / 150,000 = 1.20
    assert CompaRatioCalculator.calculate(180000.0, 150000.0) == 1.20


def test_compa_ratio_invalid_inputs():
    with pytest.raises(ValueError):
        CompaRatioCalculator.calculate(100000.0, 0.0)

    with pytest.raises(ValueError):
        CompaRatioCalculator.calculate(100000.0, -50000.0)

    with pytest.raises(ValueError):
        CompaRatioCalculator.calculate(-10000.0, 100000.0)


def test_compa_ratio_classification():
    assert CompaRatioCalculator.classify(0.75) == "BELOW_TARGET"
    assert CompaRatioCalculator.classify(0.799) == "BELOW_TARGET"
    assert CompaRatioCalculator.classify(0.80) == "TARGET_RANGE"
    assert CompaRatioCalculator.classify(1.00) == "TARGET_RANGE"
    assert CompaRatioCalculator.classify(1.20) == "TARGET_RANGE"
    assert CompaRatioCalculator.classify(1.25) == "ABOVE_TARGET"


def test_compa_ratio_analyze():
    res = CompaRatioCalculator.analyze(105000.0, 150000.0)
    assert res["compa_ratio"] == 0.70
    assert res["classification"] == "BELOW_TARGET"
    assert res["is_outlier"] is True
    assert res["deviation_from_midpoint_pct"] == -30.0
