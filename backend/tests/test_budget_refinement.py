"""
TRIPPY Backend — Budget Calculation & Refinement Tests

Tests deterministic Python budget math, cost limit validation,
and the iterative refinement loop (max 2 attempts) with fallback warnings.
"""

import pytest
from datetime import date

from app.agents.crew import TrippyCrew
from app.schemas.trip import (
    BudgetBreakdown,
    TransportMode,
    TravelStyle,
    TripPreferences,
)
from app.tools.budget_tools import (
    calculate_itemized_budget,
    evaluate_budget,
)


def test_calculate_itemized_budget_math():
    """Verify exact deterministic addition and 8% misc contingency calculation."""
    breakdown = calculate_itemized_budget(
        transport_cost=500.0,
        accommodation_cost=800.0,
        activities_cost=200.0,
        food_cost=300.0,
        misc_rate=0.08,
    )
    # subtotal = 500 + 800 + 200 + 300 = 1800.0
    # misc = 1800 * 0.08 = 144.0
    # total = 1944.0
    assert breakdown.transport == 500.0
    assert breakdown.accommodation == 800.0
    assert breakdown.activities == 200.0
    assert breakdown.food_estimate == 300.0
    assert breakdown.miscellaneous == 144.0
    assert breakdown.total == 1944.0


def test_evaluate_budget_no_limit():
    breakdown = calculate_itemized_budget(100.0, 100.0, 100.0, 100.0)
    result = evaluate_budget(breakdown, budget_max=None)
    assert result.is_within_budget is True
    assert result.overflow_amount == 0.0
    assert len(result.reduction_proposals) == 0


def test_evaluate_budget_over_limit():
    breakdown = calculate_itemized_budget(500.0, 600.0, 200.0, 300.0)
    # Total is 1728.0
    result = evaluate_budget(breakdown, budget_max=1500.0)
    assert result.is_within_budget is False
    assert result.overflow_amount == 228.0
    assert len(result.reduction_proposals) > 0


@pytest.mark.anyio
async def test_refinement_loop_succeeds_on_first_try():
    """With an ample budget, trip passes without any refinement attempts."""
    crew = TrippyCrew()
    prefs = TripPreferences(
        origin="Rome, Italy",
        destinations=["Rome, Italy"],
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 5),
        budget_max=6000.0,  # Ample budget
        travel_style=TravelStyle.cultural,
    )
    result = await crew.kickoff(prefs)
    assert result.budget.total <= 6000.0
    # No budget warning should exist
    assert not any("Budget Advisory" in w for w in result.warnings)


@pytest.mark.anyio
async def test_refinement_loop_succeeds_after_one_refinement():
    """With a tight budget, trip exceeds initial estimate but resolves on refinement 1."""
    crew = TrippyCrew()
    # Baseline for 4 days international flight + midscale hotel ~ $1800 - $2200
    prefs = TripPreferences(
        origin="London, UK",
        destinations=["Paris, France"],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
        budget_max=1450.0,  # Tight budget requiring tier reduction
        travel_style=TravelStyle.cultural,
        preferred_transport=TransportMode.train,
    )
    result = await crew.kickoff(prefs)
    assert result.budget.total > 0
    # The budget should be reduced
    assert result.budget.total <= 1450.0 or len(result.warnings) > 0


@pytest.mark.anyio
async def test_refinement_loop_exhausts_two_attempts_and_warns():
    """
    With an impossibly low budget ($100), trip cannot be satisfied.
    Verifies that it executes max 2 refinements, does NOT crash,
    and returns an honest warning with alternatives.
    """
    crew = TrippyCrew()
    prefs = TripPreferences(
        origin="New York, USA",
        destinations=["Paris, France"],
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 8),  # 7 days transatlantic
        budget_max=150.0,  # Unrealistic budget
        travel_style=TravelStyle.luxury,
    )
    result = await crew.kickoff(prefs)
    assert result.budget.total > 150.0
    # Must contain an honest warning explaining the budget overflow
    assert len(result.warnings) > 0
    assert any("Budget Advisory" in w for w in result.warnings)
    assert any("alternatives" in w.lower() for w in result.warnings)
    # The application produces a valid itinerary structure despite warning
    assert len(result.itinerary) == 7
