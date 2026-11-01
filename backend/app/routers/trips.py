"""
TRIPPY Backend — Trip Planning Router

Provides the endpoint for autonomous multi-agent trip planning.
Orchestrates Destination, Transport, Stay & Activity, Budget,
and Itinerary agents with deterministic refinement and safety fallbacks.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.schemas import TripPreferences, TripResult
from app.services import trip_service
from app.storage import trip_repository

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/plan", response_model=TripResult)
async def plan_trip(preferences: TripPreferences) -> TripResult:
    """
    Accept traveler preferences and return a full AI-planned trip.

    Orchestrates the five CrewAI specialist agents:
    1. Destination Agent: ranks candidates based on preferences and style.
    2. Transport Agent: estimates routing, durations, and costs.
    3. Stay & Activity Agent: curates accommodations, activities, and dining.
    4. Budget Agent: deterministically calculates budget and proposes reductions.
    5. Itinerary Agent: synthesizes final day-by-day itinerary.
    """
    return await trip_service.plan_trip(preferences)


@router.get("/{trip_id}", response_model=TripResult)
async def get_trip(trip_id: str) -> TripResult:
    """Retrieves a previously planned trip by its unique ID."""
    trip = trip_repository.get(trip_id)
    if not trip:
        raise HTTPException(
            status_code=404,
            detail=f"Trip with ID '{trip_id}' not found.",
        )
    return trip


@router.get("", response_model=List[TripResult])
async def list_trips(limit: int = Query(default=10, ge=1, le=50)) -> List[TripResult]:
    """Lists recently planned trips."""
    return trip_repository.list_recent(limit=limit)


