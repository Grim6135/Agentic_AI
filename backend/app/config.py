"""
TRIPPY Backend — Configuration

Loads settings from environment variables with sensible defaults.
The application runs without any external services by default.
"""

import json
from typing import Any, Union
from dotenv import load_dotenv
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


load_dotenv(".env", override=False)


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    # App & Environment
    app_name: str = "TRIPPY"
    app_version: str = "0.4.0"
    environment: str = "development"  # "development" | "production" | "testing"
    debug: bool = False

    # CORS
    cors_origins: Union[str, list[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Storage & Persistence
    storage_dir: str = ".data"
    database_url: SecretStr = SecretStr("")

    # AI Provider configuration (server-side only)
    ai_enabled: bool = False
    ai_provider: str = "groq"  # "groq" | "gemini" | "openai"
    ai_api_key: str = ""
    ai_model: str = "openai/gpt-oss-120b"
    ai_timeout_seconds: float = 15.0

    google_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    crew_model: str = "groq/openai/gpt-oss-120b"
    adk_model: str = "groq/openai/gpt-oss-120b"
    adk_base_url: str = "http://127.0.0.1:8001"
    research_service_url: str = ""
    adk_service_token: str = ""
    hourly_client_limit: int = Field(default=4, ge=1)
    hourly_global_limit: int = Field(default=20, ge=1)

    # RAG Configuration
    rag_enabled: bool = True
    rag_persist_dir: str = ".chroma"

    # External Integrations (Weather & Route APIs)
    weather_provider: str = "open-meteo"  # "open-meteo" | "mock"
    weather_api_key: str = ""
    maps_provider: str = "osrm"  # "osrm" | "mock"
    maps_api_key: str = ""
    integration_timeout_seconds: float = 5.0
    integration_cache_ttl_seconds: int = 600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra":"ignore"}

    @property
    def research_base_url(self) -> str:
        return (self.research_service_url or self.adk_base_url).rstrip("/")

    def model_key(self, model: str) -> str:
        provider = model.partition("/")[0]
        if provider == "groq":
            return self.groq_api_key
        if provider == "openrouter":
            return self.openrouter_api_key
        if provider == "gemini" or model.startswith("gemini-"):
            return self.google_api_key
        if provider == "openai":
            return self.ai_api_key
        return ""

    def masked_secrets(self) -> dict[str, str]:
        """Returns safe summary of configured credentials without leaking secrets."""
        def mask(key: str) -> str:
            if not key:
                return "not_configured"
            if len(key) <= 6:
                return "***"
            return f"{key[:3]}...{key[-3:]}"

        return {
            "ai_api_key": mask(self.ai_api_key),
            "weather_api_key": mask(self.weather_api_key),
            "maps_api_key": mask(self.maps_api_key),
        }


settings = Settings()



