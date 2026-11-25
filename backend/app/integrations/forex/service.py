"""
TRIPPY Backend — Foreign Exchange (Forex) Live Integration Service

Fetches live exchange rates via open.er-api.com (open, reliable, free exchange rates),
with in-memory TTL caching and deterministic fallback rates.
"""

from datetime import datetime
import logging
import time
from typing import Dict, Optional
import httpx

from app.config import settings

logger = logging.getLogger("trippy.forex")

# Reliable baseline rates against USD
FALLBACK_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 86.5,
    "JPY": 155.0,
    "CAD": 1.38,
    "AUD": 1.52,
    "CHF": 0.90,
    "SGD": 1.34,
    "AED": 3.67,
    "THB": 36.5,
}


class ForexService:
    """Provides live currency exchange rates with TTL caching."""

    def __init__(self, ttl_seconds: int = 86400, timeout: float = 4.0):
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self._cache: Dict[str, Tuple[float, Dict[str, float]]] = {}  # base -> (timestamp, rates)

    async def get_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """Fetches live exchange rates for the given base currency."""
        base = base_currency.upper().strip()
        now = time.time()

        if base in self._cache:
            ts, rates = self._cache[base]
            if now - ts < self.ttl_seconds:
                return rates

        # Query live API
        url = f"https://open.er-api.com/v6/latest/{base}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    rates = data.get("rates", {})
                    if rates:
                        self._cache[base] = (now, rates)
                        logger.info(f"Updated live forex rates for base {base} ({len(rates)} currencies).")
                        return rates
        except Exception as e:
            logger.warning(f"Live forex query failed for {base}: {e}. Falling back to baseline rates.")

        # Compute fallback conversion from USD baseline
        if base == "USD":
            return FALLBACK_RATES
        base_to_usd = 1.0 / FALLBACK_RATES.get(base, 1.0)
        computed = {curr: round(rate * base_to_usd, 4) for curr, rate in FALLBACK_RATES.items()}
        computed[base] = 1.0
        return computed

    async def convert(self, amount: float, from_curr: str, to_curr: str) -> float:
        """Converts an amount between two currencies using live rates."""
        from_c = from_curr.upper().strip()
        to_c = to_curr.upper().strip()
        if from_c == to_c:
            return round(amount, 2)

        rates = await self.get_rates(base_currency=from_c)
        rate = rates.get(to_c)
        if rate is None:
            # Try via USD
            usd_rates = await self.get_rates(base_currency="USD")
            usd_amount = amount / usd_rates.get(from_c, 1.0)
            rate = usd_rates.get(to_c, 1.0)
            return round(usd_amount * rate, 2)

        return round(amount * rate, 2)

    async def get_multiplier_from_usd(self, currency: str) -> float:
        """Returns the multiplier from USD to the target currency."""
        rates = await self.get_rates("USD")
        return rates.get(currency.upper().strip(), FALLBACK_RATES.get(currency.upper().strip(), 1.0))


forex_service = ForexService()
