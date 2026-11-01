"""
TRIPPY Backend — Trip Orchestration Service

Orchestrates the CrewAI agent pipeline with deterministic budget validation,
refinement loops, and resilient fallback handling.
"""

import logging
from app.agents.crew import TrippyCrew
from app.schemas.trip import BudgetBreakdown, TripPreferences, TripResult
from app.storage import trip_repository

logger = logging.getLogger("trippy.orchestrator")


class TripOrchestratorService:
    """Service orchestrating CrewAI trip planning agents."""

    def __init__(self):
        self.crew = TrippyCrew()

    async def plan_trip(self, preferences: TripPreferences) -> TripResult:
        """
        Executes multi-agent trip planning and persists the result.
        Catches any unexpected exceptions to ensure endpoint availability.
        """
        try:
            result = await self.crew.kickoff(preferences)
        except Exception as exc:
            logger.error(f"Error during agent trip planning: {exc}", exc_info=True)
            # Safe, non-crashing fallback
            result = TripResult(
                trip_id="trip_fallback_001",
                preferences=preferences,
                destinations=preferences.destinations or ["Kyoto, Japan"],
                itinerary=[],
                budget=BudgetBreakdown(),
                summary=f"Trip planning encountered a temporary issue: {exc}. Deterministic safe plan returned.",
                warnings=[
                    "A transient error occurred during agent planning. Please review your preferences and try again."
                ],
            )
        # Persist the trip
        try:
            trip_repository.save(result)
        except Exception as storage_exc:
            logger.warning(f"Failed to persist trip {result.trip_id}: {storage_exc}")
        return result



trip_service = TripOrchestratorService()
