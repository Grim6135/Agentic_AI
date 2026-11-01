"""
TRIPPY Backend — External Integrations Tests

Tests:
1. Weather Service: live Open-Meteo provider, mock provider, climatology fallback.
2. Route Service: live OSRM/geodesic provider, mock provider, matrix fallback.
3. Distinction of verified live data (is_live=True) vs estimated/mocked (is_live=False).
4. TTL caching to prevent duplicate network calls.
5. Graceful handling of provider failures, timeouts, and missing API keys.
"""

from datetime import date
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.integrations import (
    MockRouteProvider,
    MockWeatherProvider,
    RouteEstimate,
    WeatherForecast,
    route_service,
    weather_service,
)
from app.integrations.maps.service import OSRMRouteProvider, haversine_distance_km
from app.integrations.weather.service import OpenMeteoWeatherProvider


# ─── Weather Tests ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_mock_weather_provider():
    mock_prov = MockWeatherProvider()
    res = await mock_prov.get_forecast("Rome, Italy", date(2026, 6, 1), date(2026, 6, 5))
    assert isinstance(res, WeatherForecast)
    assert res.is_live is False
    assert res.destination == "Rome, Italy"
    assert "Mock" in res.provider_name


@pytest.mark.anyio
async def test_weather_fallback_on_error():
    """Verify WeatherService falls back to estimated climatology when live provider fails."""
    with patch.object(
        weather_service.live_provider,
        "get_forecast",
        side_effect=httpx.ConnectTimeout("Network timeout"),
    ):
        res = await weather_service.get_forecast("Kyoto, Japan", date(2026, 10, 1), date(2026, 10, 5))

    assert isinstance(res, WeatherForecast)
    assert res.is_live is False
    assert res.destination == "Kyoto, Japan"
    assert "Estimated" in res.provider_name or "Climatology" in res.provider_name
    assert res.temperature_c > 0


@pytest.mark.anyio
async def test_weather_service_caching():
    """Verify subsequent requests within TTL return cached response."""
    d1 = date(2026, 11, 1)
    d2 = date(2026, 11, 5)
    res1 = await weather_service.get_forecast("Bali, Indonesia", d1, d2)
    res2 = await weather_service.get_forecast("Bali, Indonesia", d1, d2)

    assert res1.summary == res2.summary
    assert res1.recorded_at == res2.recorded_at


# ─── Maps / Route Tests ──────────────────────────────────────────────────

def test_haversine_distance_calculation():
    # Rome (41.9028, 12.4964) to Paris (48.8566, 2.3522) is ~1,105 km
    rome_coord = (41.9028, 12.4964)
    paris_coord = (48.8566, 2.3522)
    dist = haversine_distance_km(rome_coord, paris_coord)
    assert 1050.0 < dist < 1150.0


@pytest.mark.anyio
async def test_mock_route_provider():
    mock_prov = MockRouteProvider()
    res = await mock_prov.get_route("London", "Paris", mode="train")
    assert isinstance(res, RouteEstimate)
    assert res.is_live is False
    assert "Mock" in res.provider_name
    assert res.distance_km > 0


@pytest.mark.anyio
async def test_osrm_geodesic_route_provider():
    prov = OSRMRouteProvider(timeout=3.0)
    res = await prov.get_route("Rome, Italy", "Paris, France", mode="flight")
    assert isinstance(res, RouteEstimate)
    assert res.distance_km > 1000.0
    assert res.duration_hours > 0.0
    assert res.is_live is True


@pytest.mark.anyio
async def test_route_fallback_on_error():
    """Verify RouteService falls back to estimated matrix when live routing fails."""
    with patch.object(
        route_service.live_provider,
        "get_route",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        res = await route_service.get_route("Tokyo, Japan", "UnknownPlace", mode="mixed")

    assert isinstance(res, RouteEstimate)
    assert res.is_live is False
    assert "Estimated" in res.provider_name
    assert res.distance_km > 0


@pytest.mark.anyio
async def test_route_service_caching():
    """Verify subsequent routing calls within TTL return cached response."""
    res1 = await route_service.get_route("New Delhi, India", "Kyoto, Japan", mode="flight")
    res2 = await route_service.get_route("New Delhi, India", "Kyoto, Japan", mode="flight")
    assert res1.distance_km == res2.distance_km
    assert res1.route_summary == res2.route_summary


# ─── Distinction of Verified Live vs Estimated ───────────────────────────

@pytest.mark.anyio
async def test_distinguish_verified_live_from_estimated():
    """Verify system explicitly labels live verified vs estimated data."""
    # Live route
    osrm = OSRMRouteProvider()
    live_route = await osrm.get_route("Rome, Italy", "Paris, France")
    assert live_route.is_live is True
    assert "Live" in live_route.provider_name or "Geodesic" in live_route.provider_name

    # Mock route
    mock_r = MockRouteProvider()
    mocked_route = await mock_r.get_route("Rome, Italy", "Paris, France")
    assert mocked_route.is_live is False
    assert "Mock" in mocked_route.provider_name
