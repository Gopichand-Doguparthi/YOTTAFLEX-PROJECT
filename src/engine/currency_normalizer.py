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

    def convert_band_to_reporting(
        self,
        band,
        to_currency: str = "USD",
        on_date: Optional[date] = None,
    ) -> Tuple[float, float, float]:
        """Converts a CompensationBand's min/mid/max salaries from local currency to reporting currency."""
        band_currency = getattr(band, "currency", to_currency) or to_currency
        ref_date = on_date or getattr(band, "effective_start_date", None) or date.today()
        rate = self.get_rate(band_currency, to_currency, ref_date)
        return (
            round(float(band.min_salary) * rate, 2),
            round(float(band.mid_salary) * rate, 2),
            round(float(band.max_salary) * rate, 2),
        )


def select_effective_band(bands: List, role_id: str, level_id: str, location_id: str, on_date: Optional[date] = None):
    """Selects the effective CompensationBand for (role, level, location) on a given date, falling back to latest ACTIVE."""
    candidates = [
        b for b in bands
        if b.role_id == role_id and b.level_id == level_id and b.location_id == location_id
    ]
    if not candidates:
        return None
    if on_date is not None:
        in_window = [
            b for b in candidates
            if b.effective_start_date <= on_date and (b.effective_end_date is None or on_date <= b.effective_end_date)
        ]
        if in_window:
            # Prefer ACTIVE if multiple overlap
            active_in_window = [b for b in in_window if getattr(b, "status", None) == "ACTIVE"]
            return active_in_window[0] if active_in_window else in_window[0]
    active = [b for b in candidates if getattr(b, "status", None) == "ACTIVE"]
    if active:
        return sorted(active, key=lambda b: b.effective_start_date, reverse=True)[0]
    return sorted(candidates, key=lambda b: b.effective_start_date, reverse=True)[0]
