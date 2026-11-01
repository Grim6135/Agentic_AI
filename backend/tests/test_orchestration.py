"""
TRIPPY Backend — Orchestration Integration Tests

Verifies that all five specialist agent roles are invoked in the
expected workflow sequence and tests error/timeout resilience.
"""

from unittest.mock import AsyncMock, patch
import pytest
from datetime import date
import httpx

from app.agents.crew import TrippyCrew
from app.schemas.trip import TripPreferences, TripResult
from app.services.orchestrator import TripOrchestratorService


@pytest.fixture
def preferences():
    return TripPreferences(
        origin="Berlin, Germany",
        destinations=["Rome, Italy"],
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 15),  # 5 days
        budget_max=3000.0,
    )


@pytest.mark.anyio
async def test_all_five_agents_invoked_in_workflow(preferences):
    """
    Integration test verifying all 5 specialist agent roles are
    registered and invoked during the planning workflow.
    """
    crew = TrippyCrew()

    # Verify registered agent roles
    agent_roles = [agent.role for agent in crew.agents]
    expected_roles = [
        "Destination Specialist",
        "Transport Specialist",
        "Stay & Activity Specialist",
        "Budget Specialist",
        "Itinerary Specialist",
    ]
    assert agent_roles == expected_roles

    call_order = []

    orig_dest = crew.destination_agent.run
    orig_trans = crew.transport_agent.run
    orig_stay = crew.stay_activity_agent.run
    orig_budget = crew.budget_agent.run
    orig_itin = crew.itinerary_agent.run

    async def mock_dest(*args, **kwargs):
        call_order.append("destination")
        return await orig_dest(*args, **kwargs)

    async def mock_trans(*args, **kwargs):
        call_order.append("transport")
        return await orig_trans(*args, **kwargs)

    async def mock_stay(*args, **kwargs):
        call_order.append("stay")
        return await orig_stay(*args, **kwargs)

    async def mock_budget(*args, **kwargs):
        call_order.append("budget")
        return await orig_budget(*args, **kwargs)

    async def mock_itin(*args, **kwargs):
        call_order.append("itinerary")
        return await orig_itin(*args, **kwargs)

    with patch.object(crew.destination_agent, "run", side_effect=mock_dest), \
         patch.object(crew.transport_agent, "run", side_effect=mock_trans), \
         patch.object(crew.stay_activity_agent, "run", side_effect=mock_stay), \
         patch.object(crew.budget_agent, "run", side_effect=mock_budget), \
         patch.object(crew.itinerary_agent, "run", side_effect=mock_itin):

        result = await crew.kickoff(preferences)

    assert isinstance(result, TripResult)
    assert "destination" in call_order
    assert "transport" in call_order
    assert "stay" in call_order
    assert "budget" in call_order
    assert "itinerary" in call_order

    # Verify initial sequence: destination must be first, itinerary must be last
    assert call_order[0] == "destination"
    assert call_order[-1] == "itinerary"


@pytest.mark.anyio
async def test_llm_provider_timeout_fallback(preferences):
    """
    When LLM provider experiences network timeout, planning must
    smoothly fall back to deterministic mode without raising an exception.
    """
    crew = TrippyCrew()

    # Mock llm_service to simulate timeout
    with patch("app.services.llm_provider.llm_service.is_available", return_value=True), \
         patch("app.services.llm_provider.llm_service.generate_structured", side_effect=httpx.TimeoutException("Read timeout")):

        result = await crew.kickoff(preferences)

    assert isinstance(result, TripResult)
    assert len(result.itinerary) == 5
    assert result.budget.total > 0


@pytest.mark.anyio
async def test_orchestrator_service_error_safety(preferences):
    """
    When an unexpected error occurs during agent execution,
    the service must return a safe TripResult without crashing the API.
    """
    service = TripOrchestratorService()

    with patch.object(service.crew, "kickoff", side_effect=RuntimeError("Simulated unexpected agent crash")):
        result = await service.plan_trip(preferences)

    assert isinstance(result, TripResult)
    assert "trip_fallback" in result.trip_id
    assert len(result.warnings) > 0
