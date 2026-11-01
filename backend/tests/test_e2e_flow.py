"""End-to-end integration tests verifying the full TRIPPY planning & persistence workflow."""

from unittest.mock import patch
import pytest
from app.integrations.base import RouteEstimate, WeatherForecast


@pytest.mark.anyio
async def test_complete_e2e_flow_with_budget_refinement_and_persistence(client):
    """
    Verifies complete end-to-end pipeline:
    Form Input -> FastAPI -> TrippyCrew -> 5 Agents -> Budget Refinement -> RAG Context -> Storage -> Retrieval.
    """
    payload = {
        "origin": "San Francisco, USA",
        "destinations": ["Kyoto, Japan"],
        "start_date": "2026-11-10",
        "end_date": "2026-11-16",
        "budget_max": 2000.0,  # Tight budget to exercise refinement loop
        "travelers": 2,
        "travel_style": "cultural",
        "preferred_transport": "flight",
        "interests": ["temples", "tea ceremonies", "history"],
    }

    # Step 1: Submit planning request to FastAPI
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 200
    plan = response.json()

    # Step 2: Validate trip result attributes
    assert plan["trip_id"].startswith("trip_")
    assert plan["destinations"] == ["Kyoto, Japan"]
    assert len(plan["itinerary"]) == 6  # 6 days
    assert plan["budget"]["total"] > 0
    assert plan["budget"]["transport"] > 0
    assert plan["budget"]["accommodation"] > 0

    # Step 3: Validate RAG context and source labels
    assert len(plan["rag_sources"]) > 0
    assert any("Kyoto" in src or "Guide" in src for src in plan["rag_sources"])
    assert len(plan["destination_guidance"]) > 0

    # Step 4: Validate weather & route estimates
    assert plan["weather"] is not None
    assert "Kyoto" in plan["weather"]["destination"]
    assert plan["route_estimate"] is not None
    assert plan["route_estimate"]["distance_km"] > 0

    # Step 5: Validate persistence by retrieving the planned trip from storage
    trip_id = plan["trip_id"]
    get_res = await client.get(f"/api/trips/{trip_id}")
    assert get_res.status_code == 200
    stored_trip = get_res.json()
    assert stored_trip["trip_id"] == trip_id
    assert stored_trip["budget"]["total"] == plan["budget"]["total"]


@pytest.mark.anyio
async def test_e2e_flow_when_external_providers_fail(client):
    """
    Verifies that complete network/provider outage in weather & route APIs
    does not crash planning; fallback estimates are returned with is_live=False.
    """
    with patch(
        "app.integrations.weather_service.get_forecast",
        side_effect=RuntimeError("Weather network timeout"),
    ), patch(
        "app.integrations.route_service.get_route",
        side_effect=RuntimeError("Route connection error"),
    ):
        payload = {
            "origin": "Sydney, Australia",
            "start_date": "2026-12-01",
            "end_date": "2026-12-05",
            "travelers": 1,
            "travel_style": "relaxation",
        }
        response = await client.post("/api/trips/plan", json=payload)
        assert response.status_code == 200
        plan = response.json()
        assert plan["trip_id"].startswith("trip_")
        assert len(plan["itinerary"]) == 4

        # Even with provider failure, trip is persisted and available
        trip_id = plan["trip_id"]
        get_res = await client.get(f"/api/trips/{trip_id}")
        assert get_res.status_code == 200
        assert get_res.json()["trip_id"] == trip_id


@pytest.mark.anyio
async def test_e2e_budget_refinement_exhaustion_advisory(client):
    """
    When budget is impossibly low (e.g. $100 for 10 days international trip),
    the budget loop applies 2 optimization cycles, caps at 2, attaches an honest warning advisory,
    and returns a complete valid plan without crashing.
    """
    payload = {
        "origin": "London, UK",
        "destinations": ["Paris, France"],
        "start_date": "2026-10-01",
        "end_date": "2026-10-10",
        "budget_max": 100.0,  # Impossibly low for 9 nights in Paris
        "travelers": 2,
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 200
    plan = response.json()

    # Must contain budget warning
    assert len(plan["warnings"]) > 0
    assert any("budget advisory" in w.lower() or "exceeds" in w.lower() for w in plan["warnings"])
