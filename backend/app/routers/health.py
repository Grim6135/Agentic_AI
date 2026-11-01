from fastapi import APIRouter

from app.config import settings
from app.rag import rag_service
from app.schemas import HealthReadyResponse, HealthResponse
from app.storage import trip_repository

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
    storage_info = trip_repository.health_status()
    rag_doc_count = 0
    try:
        rag_doc_count = rag_service.collection.count()
    except Exception:
        rag_doc_count = 0

    return HealthReadyResponse(
        status="ready",
        version=settings.app_version,
        environment=settings.environment,
        rag_enabled=settings.rag_enabled,
        rag_documents_loaded=rag_doc_count,
        weather_provider=settings.weather_provider,
        maps_provider=settings.maps_provider,
        storage_writable=storage_info.get("is_writable", False),
        stored_trips_count=storage_info.get("total_trips", 0),
    )

