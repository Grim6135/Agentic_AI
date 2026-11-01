"""
TRIPPY Backend — Pydantic Schemas

Defines data models for trip preferences (input) and trip results (output).
These schemas are used for request validation, response serialization,
and will later feed into the AI agent pipeline.
"""

from datetime import date as dt_date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Alias for external imports
date = dt_date


# ─── Enums ───────────────────────────────────────────────────────────────

class TravelStyle(str, Enum):
    adventure = "adventure"
    relaxation = "relaxation"
    cultural = "cultural"
    business = "business"
    family = "family"
    romantic = "romantic"
    budget = "budget"
    luxury = "luxury"


class TransportMode(str, Enum):
    flight = "flight"
    train = "train"
    bus = "bus"
    car = "car"
    mixed = "mixed"


# ─── Request Schemas ─────────────────────────────────────────────────────

class TripPreferences(BaseModel):
    """User-submitted travel preferences that drive the AI planning pipeline."""

    origin: str = Field(..., min_length=1, max_length=200, examples=["New Delhi, India"])
    destinations: Optional[list[str]] = Field(
        default=None,
        description="Preferred destinations; leave empty for AI suggestions.",
        examples=[["Paris, France", "Rome, Italy"]],
    )
    start_date: dt_date = Field(..., examples=["2026-12-20"])
    end_date: dt_date = Field(..., examples=["2026-12-30"])
    budget_min: Optional[float] = Field(default=None, ge=0, examples=[500.0])
    budget_max: Optional[float] = Field(default=None, ge=0, examples=[3000.0])
    currency: str = Field(default="USD", max_length=3, examples=["USD", "EUR", "INR"])
    travelers: int = Field(default=1, ge=1, le=20, examples=[2])
    travel_style: TravelStyle = Field(default=TravelStyle.cultural)
    preferred_transport: TransportMode = Field(default=TransportMode.mixed)
    interests: list[str] = Field(
        default_factory=list,
        max_length=20,
        examples=[["history", "food", "photography"]],
    )
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> "TripPreferences":
        if self.end_date <= self.start_date:
            raise ValueError("Trip end date must be after start date.")
        return self


# ─── Response Schemas ────────────────────────────────────────────────────

class TransportLeg(BaseModel):
    mode: TransportMode
    origin: str
    destination: str
    departure: Optional[str] = None
    arrival: Optional[str] = None
    cost_estimate: Optional[float] = None
    notes: Optional[str] = None


class Accommodation(BaseModel):
    name: str
    location: str
    check_in: Optional[dt_date] = None
    check_out: Optional[dt_date] = None
    cost_per_night: Optional[float] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class Activity(BaseModel):
    name: str
    location: str
    date: Optional[dt_date] = None
    duration_hours: Optional[float] = None
    cost_estimate: Optional[float] = None
    description: Optional[str] = None


class DayPlan(BaseModel):
    day: int = Field(..., ge=1)
    date: dt_date
    activities: list[Activity] = Field(default_factory=list)
    accommodation: Optional[Accommodation] = None
    transport: list[TransportLeg] = Field(default_factory=list)
    daily_budget: Optional[float] = None


class BudgetBreakdown(BaseModel):
    currency: str = "USD"
    transport: float = 0.0
    accommodation: float = 0.0
    activities: float = 0.0
    food_estimate: float = 0.0
    miscellaneous: float = 0.0
    total: float = 0.0


from app.integrations.base import RouteEstimate, WeatherForecast


class TripResult(BaseModel):
    """Complete AI-generated trip plan returned to the user."""

    trip_id: str = Field(..., examples=["trip_abc123"])
    preferences: TripPreferences
    destinations: list[str]
    currency: str = Field(default="USD")
    itinerary: list[DayPlan] = Field(default_factory=list)
    budget: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    summary: str = Field(default="", description="Human-readable trip summary.")
    warnings: list[str] = Field(default_factory=list)
    weather: Optional[WeatherForecast] = None
    route_estimate: Optional[RouteEstimate] = None
    rag_sources: list[str] = Field(default_factory=list, description="Verified guidebook sources")
    destination_guidance: list[str] = Field(default_factory=list, description="Passages retrieved from curated RAG guides")



# ─── Health ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class HealthReadyResponse(BaseModel):
    status: str = "ready"
    version: str = "0.1.0"
    environment: str = "development"
    rag_enabled: bool = True
    rag_documents_loaded: int = 0
    weather_provider: str = "open-meteo"
    maps_provider: str = "osrm"
    storage_writable: bool = True
    stored_trips_count: int = 0

