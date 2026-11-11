"""
Tests for Currency and FTE Normalization Modules.
"""
import pytest
from datetime import date
from src.engine.currency_normalizer import CurrencyNormalizer, MissingCurrencyConversionException
from src.engine.fte_normalizer import FTENormalizer, InvalidFTEException


def test_currency_conversion_same_currency():
    normalizer = CurrencyNormalizer()
    res = normalizer.normalize(100000.0, from_currency="USD", to_currency="USD")
    assert res == 100000.0
    assert normalizer.get_rate("USD", "USD") == 1.0


def test_currency_conversion_effective_dates():
    rates = [
        {"from_currency": "GBP", "to_currency": "USD", "rate": 1.25, "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
        {"from_currency": "GBP", "to_currency": "USD", "rate": 1.30, "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    ]
    normalizer = CurrencyNormalizer(rates=rates)

    rate_2024 = normalizer.get_rate("GBP", "USD", on_date=date(2024, 6, 15))
    assert rate_2024 == 1.25

    rate_2025 = normalizer.get_rate("GBP", "USD", on_date=date(2025, 6, 15))
    assert rate_2025 == 1.30

    converted = normalizer.normalize(80000.0, "GBP", "USD", on_date=date(2025, 6, 15))
    assert converted == 104000.0  # 80,000 * 1.30


def test_missing_currency_conversion_raises_exception():
    normalizer = CurrencyNormalizer(rates=[])
    # Expect MissingCurrencyConversionException for foreign currency with no rate
    with pytest.raises(MissingCurrencyConversionException) as exc_info:
        normalizer.get_rate("JPY", "USD", on_date=date(2026, 1, 1))

    assert "JPY" in str(exc_info.value)


def test_fte_annualization():
    assert FTENormalizer.annualize(120000.0, "ANNUAL") == 120000.0
    assert FTENormalizer.annualize(10000.0, "MONTHLY") == 120000.0
    assert FTENormalizer.annualize(5000.0, "BIWEEKLY") == 130000.0
    assert FTENormalizer.annualize(2000.0, "WEEKLY") == 104000.0

    with pytest.raises(ValueError):
        FTENormalizer.annualize(50000.0, "DAILY")


def test_fte_normalization_calculation():
    # Part-time employee working 0.5 FTE earning 60,000 USD raw annual
    # Full-time equivalent annualized should be 120,000 USD
    norm = FTENormalizer.normalize_salary(base_salary=60000.0, fte=0.5, pay_frequency="ANNUAL", fx_rate=1.0)
    assert norm == 120000.0

    # Part-time employee working 0.8 FTE with 80,000 GBP in 2025 (FX 1.30)
    # Annualized in USD = 80,000 * 1.30 = 104,000
    # Scaled to 1.0 FTE = 104,000 / 0.8 = 130,000
    norm_gbp = FTENormalizer.normalize_salary(base_salary=80000.0, fte=0.8, pay_frequency="ANNUAL", fx_rate=1.30)
    assert norm_gbp == 130000.0


def test_fte_invalid_bounds():
    with pytest.raises(InvalidFTEException):
        FTENormalizer.normalize_salary(base_salary=100000.0, fte=0.0)

    with pytest.raises(InvalidFTEException):
        FTENormalizer.normalize_salary(base_salary=100000.0, fte=-0.5)

    with pytest.raises(InvalidFTEException):
        FTENormalizer.normalize_salary(base_salary=100000.0, fte=1.5)


def test_detect_fte_ignored():
    # Part time employee at 0.5 FTE with 50,000 USD raw salary
    # If recorded normalized salary is 50,000 instead of 100,000, FTE was ignored
    is_ignored = FTENormalizer.is_fte_ignored(
        recorded_normalized_salary=50000.0,
        base_salary=50000.0,
        fte=0.5,
        pay_frequency="ANNUAL",
        fx_rate=1.0
    )
    assert is_ignored is True

    # If correctly normalized to 100,000, FTE was NOT ignored
    is_not_ignored = FTENormalizer.is_fte_ignored(
        recorded_normalized_salary=100000.0,
        base_salary=50000.0,
        fte=0.5,
        pay_frequency="ANNUAL",
        fx_rate=1.0
    )
    assert is_not_ignored is False
