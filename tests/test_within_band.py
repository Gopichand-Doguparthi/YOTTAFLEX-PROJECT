"""
Tests for Within-Band Position Calculation.
"""
import pytest
from src.engine.within_band import WithinBandCalculator


def test_within_band_position_calculation():
    # Min: 100k, Max: 200k (Spread: 100k)
    # Salary: 100k -> 0.0
    assert WithinBandCalculator.calculate(100000.0, 100000.0, 200000.0) == 0.0

    # Salary: 150k -> 0.5
    assert WithinBandCalculator.calculate(150000.0, 100000.0, 200000.0) == 0.5

    # Salary: 200k -> 1.0
    assert WithinBandCalculator.calculate(200000.0, 100000.0, 200000.0) == 1.0

    # Below min: 80k -> -0.2
    assert WithinBandCalculator.calculate(80000.0, 100000.0, 200000.0) == -0.2

    # Above max: 220k -> 1.2
    assert WithinBandCalculator.calculate(220000.0, 100000.0, 200000.0) == 1.2


def test_within_band_invalid_inputs():
    # max <= min
    with pytest.raises(ValueError):
        WithinBandCalculator.calculate(120000.0, 150000.0, 120000.0)

    # min <= 0
    with pytest.raises(ValueError):
        WithinBandCalculator.calculate(50000.0, -1000.0, 100000.0)


def test_within_band_zone_classification():
    assert WithinBandCalculator.classify_zone(-0.1) == "GREEN_CIRCLED"
    assert WithinBandCalculator.classify_zone(0.15) == "LOWER_QUARTILE"
    assert WithinBandCalculator.classify_zone(0.40) == "MID_LOWER"
    assert WithinBandCalculator.classify_zone(0.65) == "MID_UPPER"
    assert WithinBandCalculator.classify_zone(0.90) == "UPPER_QUARTILE"
    assert WithinBandCalculator.classify_zone(1.10) == "RED_CIRCLED"


def test_within_band_analyze():
    res = WithinBandCalculator.analyze(75000.0, 100000.0, 200000.0)
    assert res["within_band_position"] == -0.25
    assert res["zone"] == "GREEN_CIRCLED"
    assert res["is_outside_band"] is True
    assert res["is_green_circled"] is True
    assert res["is_red_circled"] is False
