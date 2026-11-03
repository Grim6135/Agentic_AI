"""
TRIPPY Backend — Agent Unit Tests

Validates the contracts, roles, goals, backstories, tools, and typed outputs
for all five CrewAI specialist agents.
"""

import pytest
from datetime import date

from app.agents import (
    BudgetAgent,
    DestinationAgent,
    ItineraryAgent,
    StayActivityAgent,
    TransportAgent,
)
from app.schemas.agent_outputs import (
    BudgetAgentOutput,
    DestinationAgentOutput,
    ItineraryAgentOutput,
    StayActivityAgentOutput,
    TransportAgentOutput,
)
from app.schemas.trip import (
    BudgetBreakdown,
    TransportMode,
    TravelStyle,
    TripPreferences,
)


@pytest.fixture
def sample_preferences():
    return TripPreferences(
        origin="San Francisco, USA",
        destinations=None,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 6),  # 5 days
        budget_min=1000.0,
        budget_max=3500.0,
        currency="USD",
        travelers=2,
        travel_style=TravelStyle.cultural,
        preferred_transport=TransportMode.flight,
        interests=["history", "art", "food"],
    )


# ─── 1. Destination Agent Tests ──────────────────────────────────────────

@pytest.mark.anyio
async def test_destination_agent_contract(sample_preferences):
    agent = DestinationAgent()
    assert agent.role == "Destination Specialist"
    assert "Analyze" in agent.goal
    assert len(agent.tools) > 0

    output = await agent.run(sample_preferences)
    assert isinstance(output, DestinationAgentOutput)
    assert output.selected_destination
    assert len(output.candidates) > 0
    assert output.candidates[0].rank == 1
    assert output.candidates[0].match_score > 0
    assert len(output.rationale) > 0


@pytest.mark.anyio
async def test_destination_agent_honors_user_destination():
    prefs = TripPreferences(
        origin="London, UK",
        destinations=["Paris, France"],
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
    )
    agent = DestinationAgent()
    output = await agent.run(prefs)
    assert output.selected_destination == "Paris, France"
    assert output.candidates[0].name == "Paris, France"


# ─── 2. Transport Agent Tests ────────────────────────────────────────────

@pytest.mark.anyio
async def test_transport_agent_contract(sample_preferences):
    agent = TransportAgent()
    assert agent.role == "Transport Specialist"
    assert "Estimate" in agent.goal

    output = await agent.run(sample_preferences, "Rome, Italy", refinement_level=0)
    assert isinstance(output, TransportAgentOutput)
    assert len(output.legs) == 2  # Outbound & return
    assert output.total_cost > 0
    assert output.total_duration_hours > 0
    assert len(output.alternatives) > 0


@pytest.mark.anyio
async def test_transport_agent_refinement_levels(sample_preferences):
    agent = TransportAgent()
    out_std = await agent.run(sample_preferences, "Rome, Italy", refinement_level=0)
    out_ref1 = await agent.run(sample_preferences, "Rome, Italy", refinement_level=1)
    out_ref2 = await agent.run(sample_preferences, "Rome, Italy", refinement_level=2)

    assert out_ref1.total_cost < out_std.total_cost
    assert out_ref2.total_cost < out_ref1.total_cost


# ─── 3. Stay & Activity Agent Tests ──────────────────────────────────────

@pytest.mark.anyio
async def test_stay_activity_agent_contract(sample_preferences):
    agent = StayActivityAgent()
    assert agent.role == "Stay & Activity Specialist"
    assert "Recommend" in agent.goal

    output = await agent.run(sample_preferences, "Rome, Italy", refinement_level=0)
    assert isinstance(output, StayActivityAgentOutput)
    assert output.accommodation_name
    assert output.cost_per_night > 0
    assert output.total_accommodation_cost > 0
    assert len(output.activities) == 5  # 5-day trip has 5 activities
    assert output.daily_food_cost > 0
    assert output.total_food_cost > 0


@pytest.mark.anyio
async def test_stay_activity_agent_refinement(sample_preferences):
    agent = StayActivityAgent()
    out_std = await agent.run(sample_preferences, "Rome, Italy", refinement_level=0)
    out_ref = await agent.run(sample_preferences, "Rome, Italy", refinement_level=2)

    assert out_ref.cost_per_night < out_std.cost_per_night
    assert out_ref.daily_food_cost < out_std.daily_food_cost
    assert out_ref.accommodation_category == "budget"


# ─── 4. Budget Agent Tests ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_budget_agent_within_limit():
    agent = BudgetAgent()
    assert agent.role == "Budget Specialist"

    breakdown = BudgetBreakdown(
        transport=500.0,
        accommodation=600.0,
        activities=200.0,
        food_estimate=300.0,
        miscellaneous=128.0,
        total=1728.0,
    )

    output = await agent.run(breakdown, budget_max=2000.0, currency="USD")
    assert isinstance(output, BudgetAgentOutput)
    assert output.is_within_budget is True
    assert output.overflow_amount == 0.0
    assert len(output.reduction_proposals) == 0


@pytest.mark.anyio
async def test_budget_agent_over_limit():
    agent = BudgetAgent()

    breakdown = BudgetBreakdown(
        transport=1000.0,
        accommodation=1500.0,
        activities=500.0,
        food_estimate=600.0,
        miscellaneous=288.0,
        total=3888.0,
    )

    output = await agent.run(breakdown, budget_max=2500.0, currency="USD")
    assert isinstance(output, BudgetAgentOutput)
    assert output.is_within_budget is False
    assert output.overflow_amount == 1388.0
    assert len(output.reduction_proposals) > 0
    categories = [p.category for p in output.reduction_proposals]
    assert "accommodation" in categories
    assert "transport" in categories


# ─── 5. Itinerary Agent Tests ────────────────────────────────────────────

@pytest.mark.anyio
async def test_itinerary_agent_contract(sample_preferences):
    dest_agent = DestinationAgent()
    trans_agent = TransportAgent()
    stay_agent = StayActivityAgent()
    budget_agent = BudgetAgent()
    itin_agent = ItineraryAgent()

    assert itin_agent.role == "Itinerary Specialist"

    dest = await dest_agent.run(sample_preferences)
    trans = await trans_agent.run(sample_preferences, dest.selected_destination)
    stay = await stay_agent.run(sample_preferences, dest.selected_destination)
    breakdown = BudgetBreakdown(
        transport=trans.total_cost,
        accommodation=stay.total_accommodation_cost,
        activities=stay.total_activities_cost,
        food_estimate=stay.total_food_cost,
        miscellaneous=100.0,
        total=1500.0,
    )
    budget = await budget_agent.run(breakdown, budget_max=sample_preferences.budget_max)

    output = await itin_agent.run(
        preferences=sample_preferences,
        destination=dest.selected_destination,
        transport=trans,
        stay_activity=stay,
        budget=budget,
    )

    assert isinstance(output, ItineraryAgentOutput)
    assert len(output.days) == 5
    assert output.days[0].day == 1
    assert output.days[4].day == 5
    assert output.trip_title
    assert output.summary
    assert len(output.travel_tips) > 0


# ─── 6. CrewAI & Google ADK Framework Tests ─────────────────────────────

def test_crewai_framework_export():
    from app.agents import TrippyCrew
    crew = TrippyCrew()
    crewai_spec = crew.as_crewai_crew()
    assert "agents" in crewai_spec
    assert len(crewai_spec["agents"]) == 5
    assert crewai_spec["process"] == "sequential"
    assert len(crewai_spec["tasks"]) == 5

    # Check individual agent CrewAI contract
    dest_spec = crew.destination_agent.as_crewai_agent()
    assert dest_spec["role"] == "Destination Specialist"
    assert "goal" in dest_spec
    assert "backstory" in dest_spec
    assert "tools" in dest_spec


def test_google_adk_framework_export():
    import google.adk as adk
    from app.agents import TrippyCrew, adk_workflow_service
    crew = TrippyCrew()

    # Verify Google ADK Agent instances
    adk_agent = crew.destination_agent.as_adk_agent()
    assert isinstance(adk_agent, adk.Agent)
    assert adk_agent.name == "DestinationSpecialist"
    assert "Destination Specialist" in adk_agent.description

    # Verify Google ADK Workflow instance
    wf = crew.as_adk_workflow()
    assert isinstance(wf, adk.Workflow)
    assert wf.name == "TrippyMultiAgentPlanningWorkflow"

    info = adk_workflow_service.get_framework_info()
    assert info["status"] == "ready"
    assert len(info["registered_agents"]) == 5

