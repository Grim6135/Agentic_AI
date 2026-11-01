"""Tests for configuration parsing, CORS security, and secret masking."""

from app.config import Settings


def test_cors_origins_parsing_from_comma_separated_string():
    """Settings should parse comma-separated CORS_ORIGINS string into a list."""
    s = Settings(cors_origins="https://trippy.vercel.app, https://trippy.onrender.com, http://localhost:5173")
    assert isinstance(s.cors_origins, list)
    assert len(s.cors_origins) == 3
    assert "https://trippy.vercel.app" in s.cors_origins
    assert "https://trippy.onrender.com" in s.cors_origins
    assert "http://localhost:5173" in s.cors_origins


def test_cors_origins_parsing_from_json_string():
    """Settings should parse JSON array CORS_ORIGINS string."""
    s = Settings(cors_origins='["https://my-domain.com", "http://localhost:3000"]')
    assert isinstance(s.cors_origins, list)
    assert "https://my-domain.com" in s.cors_origins
    assert "http://localhost:3000" in s.cors_origins


def test_cors_origins_list_unchanged():
    """Settings should retain list input without modification."""
    s = Settings(cors_origins=["https://trippy.app"])
    assert s.cors_origins == ["https://trippy.app"]


def test_secret_masking_does_not_leak_keys():
    """masked_secrets() should never return plain text credentials."""
    s = Settings(
        ai_api_key="sk-openai-secret-key-99999",
        weather_api_key="openmeteo-secret-1234",
        maps_api_key="osrm-secret-token-5678",
    )
    masked = s.masked_secrets()

    for field, masked_val in masked.items():
        assert masked_val != "not_configured"
        # Must not contain the full secret
        assert "secret-key-99999" not in masked_val
        assert "secret-1234" not in masked_val
        assert "secret-token-5678" not in masked_val
        # Must have mask indicators
        assert "..." in masked_val or "***" in masked_val


def test_empty_secrets_reported_as_not_configured():
    """When secrets are empty, masked_secrets reports 'not_configured'."""
    s = Settings(ai_api_key="", weather_api_key="", maps_api_key="")
    masked = s.masked_secrets()
    assert masked["ai_api_key"] == "not_configured"
    assert masked["weather_api_key"] == "not_configured"
    assert masked["maps_api_key"] == "not_configured"


def test_default_timeouts_are_reasonable():
    """Verify timeout defaults protect against hung external calls."""
    s = Settings()
    assert s.integration_timeout_seconds <= 10.0
    assert s.ai_timeout_seconds <= 30.0
    assert s.integration_cache_ttl_seconds >= 60
