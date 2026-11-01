"""Tests for API input validation, constraints, and error reporting."""

import pytest


@pytest.mark.anyio
async def test_validation_date_order_rejected(client):
    """POST /api/trips/plan where end_date <= start_date must return HTTP 422."""
    payload = {
        "origin": "Paris, France",
        "start_date": "2026-12-25",
        "end_date": "2026-12-20",  # Prior to start_date
        "travelers": 1,
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Verify the error message notes the date issue
    error_msgs = [err.get("msg", "") for err in data["detail"]]
    assert any("end date must be after start date" in msg.lower() for msg in error_msgs)


@pytest.mark.anyio
async def test_validation_same_start_and_end_date_rejected(client):
    """POST /api/trips/plan where end_date == start_date must return HTTP 422."""
    payload = {
        "origin": "Tokyo, Japan",
        "start_date": "2026-11-10",
        "end_date": "2026-11-10",
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_validation_negative_budget_rejected(client):
    """POST /api/trips/plan with negative budget must return HTTP 422."""
    payload = {
        "origin": "New York, USA",
        "start_date": "2026-11-10",
        "end_date": "2026-11-15",
        "budget_max": -500.0,
    }
    response = await client.post("/api/trips/plan", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_validation_invalid_traveler_count(client):
    """POST /api/trips/plan with travelers < 1 or > 20 must return HTTP 422."""
    # Zero travelers
    res_zero = await client.post(
        "/api/trips/plan",
        json={
            "origin": "Berlin, Germany",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
            "travelers": 0,
        },
    )
    assert res_zero.status_code == 422

    # Excessive travelers (> 20)
    res_excess = await client.post(
        "/api/trips/plan",
        json={
            "origin": "Berlin, Germany",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
            "travelers": 25,
        },
    )
    assert res_excess.status_code == 422


@pytest.mark.anyio
async def test_validation_invalid_enum_rejected(client):
    """POST /api/trips/plan with invalid travel_style or preferred_transport returns 422."""
    res_style = await client.post(
        "/api/trips/plan",
        json={
            "origin": "Kyoto, Japan",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
            "travel_style": "unknown_style_123",
        },
    )
    assert res_style.status_code == 422

    res_transport = await client.post(
        "/api/trips/plan",
        json={
            "origin": "Kyoto, Japan",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
            "preferred_transport": "teleportation",
        },
    )
    assert res_transport.status_code == 422


@pytest.mark.anyio
async def test_validation_empty_origin_rejected(client):
    """POST /api/trips/plan with empty origin returns 422."""
    response = await client.post(
        "/api/trips/plan",
        json={
            "origin": "",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
        },
    )
    assert response.status_code == 422
