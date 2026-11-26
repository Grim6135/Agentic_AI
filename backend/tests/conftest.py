"""Exercise the actual API, A2A handler, MCP SDK, budget and storage without provider charges."""

import httpx
import pytest
from app.adk_service.server import adk_app
from app.config import settings
from app.main import app
from app.planning import workflow
from app.planning.specialists import Narrative, PlannedDay


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "adk_service_token", "test-service-token")
    monkeypatch.setattr(settings, "groq_api_key", "test-only")
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "weather_provider", "mock")
    monkeypatch.setattr(settings, "maps_provider", "mock")

    async def resolve(city):
        return (35.0, 135.0)

    async def research(p):
        return {
            "destination": (p.destinations or ["Kyoto, Japan"])[0],
            "summary": "Test research",
            "latitude": 35.0,
            "longitude": 135.0,
            "events": [],
        }

    async def crew(context):
        return Narrative(
            summary="Controlled provider response.",
            lodging_category="Guesthouse",
            days=[
                PlannedDay(activity="Walk", description="Explore the neighborhood.")
                for _ in range(context["days"])
            ],
        ), []

    async def places(*args, **kwargs):
        return None

    monkeypatch.setattr("app.routers.trips.resolve", resolve)
    monkeypatch.setattr("app.adk_service.server.research", research)
    monkeypatch.setattr(
        workflow,
        "research_client",
        lambda: httpx.AsyncClient(transport=httpx.ASGITransport(app=adk_app)),
    )
    monkeypatch.setattr(workflow, "execute_crew", crew)
    monkeypatch.setattr("app.integrations.places_service.get_destination_info", places)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac
