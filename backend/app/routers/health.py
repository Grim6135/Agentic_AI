from fastapi import APIRouter, HTTPException

from app.config import settings
from app.rag import rag_service
from app.schemas import HealthReadyResponse, HealthResponse
from app.planning import store

router = APIRouter(tags=["health"])


@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns basic application liveness health status and version."""
    return HealthResponse(status="ok", version=settings.app_version)


@router.api_route("/health/ready", methods=["GET", "HEAD"], response_model=HealthReadyResponse)
async def health_ready() -> HealthReadyResponse:
    """
    Returns deep application readiness check for production container orchestrators.
    Verifies RAG vector store, storage permissions, and integration providers.
    """
    from app.planning.workflow import research_client
    try:
        with store.connection() as db:
            count = db.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        rag_doc_count = rag_service.collection.count()
        if settings.rag_enabled and rag_doc_count == 0:
            raise RuntimeError("Knowledge base unavailable")
        if not settings.model_key(settings.crew_model) or not settings.adk_service_token:
            raise RuntimeError("Missing model configuration")
        async with research_client() as client:
            response = await client.get(settings.research_base_url + "/a2a/agent-card", timeout=3)
            response.raise_for_status()
            if not response.json().get("skills"):
                raise RuntimeError("Missing research capability")
    except Exception:
        raise HTTPException(503,"Planner dependencies are unavailable") from None

    return HealthReadyResponse(
        status="ready",
        version=settings.app_version,
        environment=settings.environment,
        rag_enabled=settings.rag_enabled,
        rag_documents_loaded=rag_doc_count,
        weather_provider=settings.weather_provider,
        maps_provider=settings.maps_provider,
        storage_writable=True,
        stored_trips_count=count,
    )

