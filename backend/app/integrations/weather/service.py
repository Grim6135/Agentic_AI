"""
TRIPPY Backend — Weather Integration Service

Isolated provider interfaces for live weather data (Open-Meteo),
mock test implementations, and deterministic climatology fallbacks.
Includes in-memory TTL caching and strict timeout enforcement.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
import logging
import time
from typing import Dict, Optional, Tuple
import httpx

from app.config import settings
from app.integrations.base import WeatherForecast

logger = logging.getLogger("trippy.weather")

WMO_WEATHER_CODES = {
    0: "Clear Sky ☀️",
    1: "Mainly Clear 🌤️",
    2: "Partly Cloudy ⛅",
    3: "Overcast ☁️",
    45: "Foggy 🌫️",
    48: "Depositing Rime Fog 🌫️",
    51: "Light Drizzle 🌦️",
    53: "Moderate Drizzle 🌧️",
    55: "Dense Drizzle 🌧️",
    61: "Slight Rain 🌦️",
    63: "Moderate Rain 🌧️",
    65: "Heavy Rain 🌧️",
    71: "Slight Snow 🌨️",
    73: "Moderate Snow ❄️",
    75: "Heavy Snow ❄️",
    80: "Rain Showers 🌦️",
    81: "Moderate Showers 🌧️",
    82: "Violent Showers ⛈️",
    95: "Thunderstorm ⛈️",
}

ESTIMATED_SEASONAL_CLIMATE = {
    "Kyoto": (19.5, "Mild & Pleasant 🍁", 15.0),
    "Rome": (22.0, "Sunny Mediterranean ☀️", 10.0),
    "Bali": (29.5, "Tropical Warm 🌴", 35.0),
    "Paris": (17.0, "Temperate & Breezy 🌤️", 20.0),
    "Swiss": (12.0, "Alpine Cool 🏔️", 25.0),
    "Barcelona": (23.0, "Warm & Coastal 🏖️", 10.0),
}


# ─── Provider Interface ──────────────────────────────────────────────────

class WeatherProvider(ABC):
    """Abstract interface for weather data providers."""

    @abstractmethod
    async def get_forecast(
        self, destination: str, start_date: date, end_date: date
    ) -> Optional[WeatherForecast]:
        pass


# ─── 1. Open-Meteo Live Provider ─────────────────────────────────────────

class OpenMeteoWeatherProvider(WeatherProvider):
    """
    Live verified weather forecasting via Open-Meteo public REST API.
    Zero API key required; live geocoding & satellite forecasts.
    """

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def get_forecast(
        self, destination: str, start_date: date, end_date: date
    ) -> Optional[WeatherForecast]:
        city_name = destination.split(",")[0].strip()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. Geocode city
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
            geo_resp = await client.get(geo_url)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

            results = geo_data.get("results", [])
            if not results:
                logger.info(f"Open-Meteo geocoding found no match for {city_name}.")
                return None

            lat = results[0]["latitude"]
            lon = results[0]["longitude"]

            # 2. Get 7-day daily forecast
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_probability_mean,weathercode&timezone=auto"
            )
            w_resp = await client.get(weather_url)
            w_resp.raise_for_status()
            w_data = w_resp.json()

            daily = w_data.get("daily", {})
            temps = daily.get("temperature_2m_max", [20.0])
            precips = daily.get("precipitation_probability_mean", [10.0])
            codes = daily.get("weathercode", [0])

            avg_temp = round(sum(temps) / len(temps), 1) if temps else 20.0
            avg_precip = round(sum(precips) / len(precips), 1) if precips else 10.0
            most_common_code = max(set(codes), key=codes.count) if codes else 0
            condition_str = WMO_WEATHER_CODES.get(most_common_code, "Partly Cloudy ⛅")

            summary = (
                f"Verified live forecast for {city_name}: Daily highs averaging {avg_temp}°C with {condition_str} "
                f"and {avg_precip:.0f}% chance of precipitation."
            )

            return WeatherForecast(
                destination=destination,
                temperature_c=avg_temp,
                condition=condition_str,
                precipitation_chance=avg_precip,
                summary=summary,
                is_live=True,
                provider_name="Open-Meteo Live API",
            )


# ─── 2. Mock Weather Provider ────────────────────────────────────────────

class MockWeatherProvider(WeatherProvider):
    """Deterministic mock provider for unit and contract testing."""

    async def get_forecast(
        self, destination: str, start_date: date, end_date: date
    ) -> Optional[WeatherForecast]:
        return WeatherForecast(
            destination=destination,
            temperature_c=21.5,
            condition="Sunny & Clear ☀️",
            precipitation_chance=5.0,
            summary=f"Mock weather for {destination}: 21.5°C, Sunny & Clear.",
            is_live=False,
            provider_name="Mock Weather Provider",
        )


# ─── 3. Estimated Fallback Provider ──────────────────────────────────────

class ClimatologyFallbackWeatherProvider(WeatherProvider):
    """Offline estimated seasonal climate data when external APIs are unavailable."""

    async def get_forecast(
        self, destination: str, start_date: date, end_date: date
    ) -> WeatherForecast:
        key = next((k for k in ESTIMATED_SEASONAL_CLIMATE if k.lower() in destination.lower()), None)
        if key:
            temp, cond, precip = ESTIMATED_SEASONAL_CLIMATE[key]
        else:
            temp, cond, precip = (20.0, "Temperate & Variable ⛅", 15.0)

        summary = (
            f"Estimated seasonal baseline for {destination}: Typical highs around {temp}°C, "
            f"{cond}, with ~{precip:.0f}% expected rain days."
        )

        return WeatherForecast(
            destination=destination,
            temperature_c=temp,
            condition=cond,
            precipitation_chance=precip,
            summary=summary,
            is_live=False,
            provider_name="Estimated Seasonal Average",
        )


# ─── Weather Service with In-Memory TTL Cache ────────────────────────────

class WeatherService:
    """Manages weather provider selection, caching, and fallback protection."""

    def __init__(self):
        self.live_provider = OpenMeteoWeatherProvider(timeout=settings.integration_timeout_seconds)
        self.mock_provider = MockWeatherProvider()
        self.fallback_provider = ClimatologyFallbackWeatherProvider()
        # In-memory cache: (dest, start_date, end_date) -> (timestamp, WeatherForecast)
        self._cache: Dict[Tuple[str, str, str], Tuple[float, WeatherForecast]] = {}
        self.cache_ttl = settings.integration_cache_ttl_seconds

    async def get_forecast(
        self, destination: str, start_date: date, end_date: date
    ) -> WeatherForecast:
        cache_key = (destination.lower(), str(start_date), str(end_date))
        now = time.time()

        if cache_key in self._cache:
            timestamp, cached_result = self._cache[cache_key]
            if now - timestamp < self.cache_ttl:
                return cached_result

        # Select provider based on configuration
        if settings.weather_provider == "mock":
            res = await self.mock_provider.get_forecast(destination, start_date, end_date)
            if res:
                self._cache[cache_key] = (now, res)
                return res

        # Try live provider
        try:
            live_res = await self.live_provider.get_forecast(destination, start_date, end_date)
            if live_res:
                self._cache[cache_key] = (now, live_res)
                return live_res
        except Exception as err:
            logger.warning(f"Live weather lookup failed for {destination}: {err}. Falling back to climatology.")

        # Fallback to seasonal estimation
        fallback_res = await self.fallback_provider.get_forecast(destination, start_date, end_date)
        self._cache[cache_key] = (now, fallback_res)
        return fallback_res


weather_service = WeatherService()
