"""
TRIPPY Backend — FastAPI Application Entry Point

Creates and configures the FastAPI application with CORS,
routers, and middleware. Runs without any external services.
"""

import os
import sys
from pathlib import Path

# Auto re-exec with virtual environment python if invoked with system python
backend_root_path = Path(__file__).resolve().parents[1]
if sys.prefix == sys.base_prefix and not os.environ.get("_TRIPPY_VENV_BOOTSTRAPPED"):
    for venv_py in [
        backend_root_path / ".venv" / "bin" / "python",
        Path("/home/Grim6135/B. Tech - CSE/Trippy/backend/.venv/bin/python"),
    ]:
        if venv_py.exists():
            env = os.environ.copy()
            env["_TRIPPY_VENV_BOOTSTRAPPED"] = "1"
            env["PYTHONPATH"] = str(backend_root_path) + (":" + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
            os.execve(str(venv_py), [str(venv_py)] + sys.argv, env)

backend_root = str(backend_root_path)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health_router, trips_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: startup and shutdown hooks."""
    # Startup
    print(f"🚀 {settings.app_name} v{settings.app_version} starting up…")
    yield
    # Shutdown
    print(f"👋 {settings.app_name} shutting down…")


def create_app() -> FastAPI:
    """Factory function that builds and returns the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Autonomous AI travel planner with five specialist agents.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    has_wildcard = "*" in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if not has_wildcard else ["*"],
        allow_credentials=not has_wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.api_route("/", methods=["GET", "HEAD"])
    async def root():
        """Root endpoint confirming API is running and linking to docs."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/health",
        }

    # Mount health at both /health and /api/health for convenience
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api")

    # API routers
    app.include_router(trips_router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

