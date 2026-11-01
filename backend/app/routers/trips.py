"""
TRIPPY Backend — Trip Planning Router

Provides the endpoint for autonomous multi-agent trip planning.
Orchestrates Destination, Transport, Stay & Activity, Budget,
and Itinerary agents with deterministic refinement and safety fallbacks.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.schemas import TripPreferences, TripResult
from app.services import location_verifier, trip_service
from app.storage import trip_repository

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/plan", response_model=TripResult)
async def plan_trip(preferences: TripPreferences) -> TripResult:
    """
    Accept traveler preferences and return a full AI-planned trip.
    Validates geographical locations and realistic monetary constraints before planning.
    """
    # 1. Verify origin location exists on Earth
    orig_check = await location_verifier.verify_location(preferences.origin)
    if not orig_check.is_valid:
        raise HTTPException(
            status_code=422,
            detail=orig_check.error_message or f"Invalid origin: '{preferences.origin}' is not a recognized city or destination.",
        )

    # 2. Verify destination locations exist on Earth
    if preferences.destinations:
        for dest in preferences.destinations:
            dest_check = await location_verifier.verify_location(dest)
            if not dest_check.is_valid:
                raise HTTPException(
                    status_code=422,
                    detail=dest_check.error_message or f"Invalid destination: '{dest}' is not a recognized city or destination.",
                )

    # 3. Monetary sanity check
    if preferences.budget_max is not None and preferences.budget_max <= 0:
        raise HTTPException(
            status_code=422,
            detail="Budget limit must be greater than 0.",
        )

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


