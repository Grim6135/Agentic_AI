"""Tests for the health endpoint."""

import pytest


@pytest.mark.anyio
async def test_health_returns_ok(client):
    """GET /api/health should return status ok and a version string."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.anyio
async def test_health_version_matches_config(client):
    """Health version should match the configured app version."""
    from app.config import settings

    response = await client.get("/api/health")
    assert response.json()["version"] == settings.app_version


@pytest.mark.anyio
async def test_health_ready_endpoint(client):
    """GET /api/health/ready should return system readiness and status metrics."""
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "rag_enabled" in data
    assert "storage_writable" in data
    assert "stored_trips_count" in data
    assert "weather_provider" in data
    assert "maps_provider" in data

