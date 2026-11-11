"""
Currency Normalization Module.
Converts local currencies to standardized reporting currency (USD) using effective-dated exchange rates.
Enforces strict exception handling when exchange rates are unavailable.
"""
from datetime import date
from typing import Dict, Optional, Tuple, List


class MissingCurrencyConversionException(Exception):
    """Raised when an exchange rate is missing for a given currency and effective date."""
    def __init__(self, currency: str, effective_date: date, message: Optional[str] = None):
        self.currency = currency
        self.effective_date = effective_date
        msg = message or f"No effective exchange rate found for currency '{currency}' on date {effective_date}."
        super().__init__(msg)


class CurrencyNormalizer:
    """Service to normalize monetary amounts using an in-memory or database-backed rate table."""

    def __init__(self, rates: Optional[List[Dict]] = None):
        # Cache rates as list of dicts:
        # [{"from_currency": "GBP", "to_currency": "USD", "rate": 1.30, "effective_start_date": date, "effective_end_date": date}]
        self.rates: List[Dict] = rates or []

    def load_from_db(self, session):
        """Loads all exchange rates from the database into the normalizer."""
        from src.database.models import ExchangeRate
        db_rates = session.query(ExchangeRate).all()
        self.rates = [
            {
                "from_currency": r.from_currency,
                "to_currency": r.to_currency,
                "rate": float(r.rate),
                "effective_start_date": r.effective_start_date,
                "effective_end_date": r.effective_end_date,
            }
            for r in db_rates
        ]

    def get_rate(self, from_currency: str, to_currency: str = "USD", on_date: Optional[date] = None) -> float:
        """
        Retrieves the effective exchange rate.
        Throws MissingCurrencyConversionException if unavailable.
        Never silently defaults to 1.0 for non-reporting currencies.
        """
        if from_currency == to_currency:
            return 1.0

        if on_date is None:
            on_date = date.today()

        # Handle string dates if passed
        if isinstance(on_date, str):
            from datetime import datetime
            on_date = datetime.strptime(on_date, "%Y-%m-%d").date()

        for r in self.rates:
            if r["from_currency"] == from_currency and r["to_currency"] == to_currency:
                start = r["effective_start_date"]
                end = r["effective_end_date"]
                if isinstance(start, str):
                    from datetime import datetime
                    start = datetime.strptime(start, "%Y-%m-%d").date()
                if isinstance(end, str):
                    from datetime import datetime
                    end = datetime.strptime(end, "%Y-%m-%d").date()

                if start <= on_date <= end:
                    return float(r["rate"])

        raise MissingCurrencyConversionException(
            currency=from_currency,
            effective_date=on_date,
            message=f"Mandatory Edge Case 3: Currency conversion missing for {from_currency}->{to_currency} on {on_date}"
        )

    def normalize(self, amount: float, from_currency: str, to_currency: str = "USD", on_date: Optional[date] = None) -> float:
        """Normalizes a raw local amount to reporting currency."""
        rate = self.get_rate(from_currency, to_currency, on_date)
        return round(amount * rate, 2)
