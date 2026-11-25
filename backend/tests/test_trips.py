"""Tests for trip schemas and the /api/trips/plan endpoint."""

import pytest
from datetime import date


@pytest.mark.anyio
async def test_plan_trip_success(client):
    """POST /api/trips/plan should accept valid preferences and return a full trip result."""
    payload = {
        "origin": "New Delhi, India",
        "start_date": "2026-12-20",
        "end_date": "2026-12-30",
        "travelers": 2,
        "travel_style": "cultural",
        "interests": ["history", "food"],
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["trip_id"].startswith("trip_")
    assert data["preferences"]["origin"] == "New Delhi, India"
    assert len(data["destinations"]) > 0
    assert len(data["itinerary"]) == 10  # 10 days
    assert data["budget"]["total"] > 0
    assert len(data["summary"]) > 0



@pytest.mark.anyio
async def test_plan_trip_validation_error(client):
    """POST /api/trips/plan with missing required fields should return 422."""
    response = await client.post("/api/trips/plan", json={})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_plan_trip_date_order(client):
    """POST /api/trips/plan with valid dates should succeed."""
    payload = {
        "origin": "London, UK",
        "start_date": "2026-06-01",
        "end_date": "2026-06-10",
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 200


def test_trip_preferences_schema():
    """TripPreferences should validate and set defaults correctly."""
    from app.schemas import TripPreferences

    prefs = TripPreferences(
        origin="Tokyo, Japan",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 10),
    )
    assert prefs.travelers == 1
    assert prefs.currency == "USD"
    assert prefs.travel_style.value == "cultural"
    assert prefs.preferred_transport.value == "mixed"
    assert prefs.interests == []


def test_trip_preferences_rejects_invalid():
    """TripPreferences should reject invalid input."""
    from pydantic import ValidationError
    from app.schemas import TripPreferences

    with pytest.raises(ValidationError):
        TripPreferences(
            origin="",  # min_length=1
            start_date="2026-12-20",
            end_date="2026-12-30",
        )
