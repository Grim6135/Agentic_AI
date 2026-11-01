"""
TRIPPY Backend — External Integrations Data Contracts

Typed schemas for Weather and Maps/Route integration responses.
Explicitly distinguishes verified live information from estimated/mocked data.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class WeatherForecast(BaseModel):
    """Weather conditions for a destination."""
    destination: str
    temperature_c: float = Field(..., description="Average high temperature in Celsius")
    condition: str = Field(..., description="E.g. Sunny, Part Cloudy, Rain Showers")
    precipitation_chance: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage")
    summary: str
    is_live: bool = Field(default=False, description="True if verified from live API, False if estimated/mocked")
    provider_name: str = Field(default="Estimated Climatology", description="Data source name")
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))



class RouteEstimate(BaseModel):
    """Route, distance, and transit estimate between origin and destination."""
    origin: str
    destination: str
    distance_km: float = Field(..., ge=0.0, description="Estimated or verified distance in kilometers")
    duration_hours: float = Field(..., ge=0.0, description="Estimated or verified travel time in hours")
    mode: str = Field(default="mixed", description="flight, train, car, bus, mixed")
    is_live: bool = Field(default=False, description="True if verified from live routing API, False if estimated")
    provider_name: str = Field(default="Deterministic Distance Matrix", description="Source provider")
    route_summary: str = ""
