"""Tests for trip storage and persistence layer."""

import tempfile
import pytest
from app.schemas.trip import BudgetBreakdown, TripPreferences, TripResult
from app.storage.repository import TripRepository


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo = TripRepository(storage_dir=tmp_dir)
        yield repo


def create_dummy_trip(trip_id: str = "trip_test_001") -> TripResult:
    prefs = TripPreferences(
        origin="Tokyo, Japan",
        start_date="2026-11-10",
        end_date="2026-11-15",
    )
    return TripResult(
        trip_id=trip_id,
        preferences=prefs,
        destinations=["Kyoto, Japan"],
        itinerary=[],
        budget=BudgetBreakdown(total=1200.0),
        summary="A test trip.",
        warnings=[],
    )


def test_save_and_retrieve_trip(temp_repo):
    """Saving a trip should make it retrievable by ID."""
    trip = create_dummy_trip("trip_save_123")
    saved = temp_repo.save(trip)
    assert saved.trip_id == "trip_save_123"

    retrieved = temp_repo.get("trip_save_123")
    assert retrieved is not None
    assert retrieved.trip_id == "trip_save_123"
    assert retrieved.budget.total == 1200.0


def test_get_nonexistent_trip_returns_none(temp_repo):
    """Querying an unknown trip ID returns None."""
    assert temp_repo.get("nonexistent_id") is None


def test_list_recent_trips(temp_repo):
    """Repository should return recent trips ordered up to limit."""
    for i in range(5):
        trip = create_dummy_trip(f"trip_batch_{i}")
        temp_repo.save(trip)

    assert temp_repo.count() == 5
    recent = temp_repo.list_recent(limit=3)
    assert len(recent) == 3
    # Most recent should be the last ones added
    assert recent[-1].trip_id == "trip_batch_4"


def test_storage_reload_from_disk():
    """A new repository instance on the same directory should load persisted trips."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo1 = TripRepository(storage_dir=tmp_dir)
        trip = create_dummy_trip("trip_disk_001")
        repo1.save(trip)

        # Create second repo on same directory
        repo2 = TripRepository(storage_dir=tmp_dir)
        assert repo2.count() == 1
        loaded = repo2.get("trip_disk_001")
        assert loaded is not None
        assert loaded.trip_id == "trip_disk_001"


def test_storage_health_status(temp_repo):
    """Storage health status should return status ok, directory, and writable flag."""
    status = temp_repo.health_status()
    assert status["status"] == "ok"
    assert status["is_writable"] is True
    assert status["total_trips"] == 0


@pytest.mark.anyio
async def test_get_trip_api_endpoint(client):
    """GET /api/trips/{trip_id} should return 404 for unknown, 200 for stored."""
    # Unknown trip
    response = await client.get("/api/trips/trip_definitely_not_here")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Plan a trip to generate and store one
    payload = {
        "origin": "Rome, Italy",
        "start_date": "2026-11-20",
        "end_date": "2026-11-25",
    }
    plan_resp = await client.post("/api/trips/plan", json=payload)
    assert plan_resp.status_code == 200
    planned_trip = plan_resp.json()
    trip_id = planned_trip["trip_id"]

    # Now retrieve it
    get_resp = await client.get(f"/api/trips/{trip_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["trip_id"] == trip_id

    # List trips endpoint
    list_resp = await client.get("/api/trips?limit=5")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
