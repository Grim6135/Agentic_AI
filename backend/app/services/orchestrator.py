"""
TRIPPY Backend — Trip Orchestration Service

Orchestrates the CrewAI agent pipeline with deterministic budget validation,
refinement loops, and resilient fallback handling.
"""

import logging
from app.agents.crew import TrippyCrew
from app.schemas.trip import TripPreferences, TripResult
from app.storage import trip_repository

logger = logging.getLogger("trippy.orchestrator")


class TripOrchestratorService:
    """Service orchestrating CrewAI trip planning agents."""

    def __init__(self):
        self.crew = TrippyCrew()

    async def plan_trip(self, preferences: TripPreferences) -> TripResult:
        """
        Executes multi-agent trip planning and persists the result.
        Propagates planning failures to the caller.
        """
        result = await self.crew.kickoff(preferences)
        # Persist the trip
        try:
            trip_repository.save(result)
        except Exception as storage_exc:
            logger.warning("Trip persistence failed (%s)", type(storage_exc).__name__)
        return result



trip_service = TripOrchestratorService()
