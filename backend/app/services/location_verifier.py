"""
TRIPPY Backend — Location Verification Service

Verifies whether user-submitted origin and destination locations are real,
recognized geographical cities, towns, or travel destinations on Earth.
Rejects gibberish entries (e.g. 'vuvv', 'dg', 'xyz') with clean user-facing diagnostics.
"""

import logging
from typing import Optional, Tuple
import httpx
from pydantic import BaseModel
from app.services.llm_provider import llm_service

logger = logging.getLogger("trippy.verifier")


class LocationVerificationResult(BaseModel):
    is_valid: bool
    canonical_name: Optional[str] = None
    country: Optional[str] = None
    error_message: Optional[str] = None


class LocationVerifier:
    """Verifies location validity using Open-Meteo Geocoding + LLM Fallback."""

    def __init__(self, timeout: float = 4.0):
        self.timeout = timeout

    async def verify_location(self, location_str: str) -> LocationVerificationResult:
        """
        Validates if a location string represents a real place on Earth.
        Returns LocationVerificationResult with canonical information or an error message.
        """
        raw = location_str.strip()
        if not raw or len(raw) < 2:
            return LocationVerificationResult(
                is_valid=False,
                error_message=f"Location '{location_str}' is too short or empty.",
            )

        clean_name = raw.split(",")[0].strip()

        # Step 1: Query Open-Meteo Geocoding API
        try:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={clean_name}&count=5&language=en&format=json"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    if results:
                        top = results[0]
                        matched_name = top.get("name", clean_name)
                        matched_country = top.get("country", "")
                        return LocationVerificationResult(
                            is_valid=True,
                            canonical_name=f"{matched_name}, {matched_country}" if matched_country else matched_name,
                            country=matched_country,
                        )
        except Exception as e:
            logger.debug(f"Geocoding lookup failed for '{clean_name}': {e}")

        # Step 2: If geocoder returned 0 matches, verify via LLM if available
        if llm_service.is_available():
            try:
                class LLMLocationCheck(BaseModel):
                    is_real_location: bool
                    canonical_name: Optional[str] = None
                    country: Optional[str] = None
                    explanation: str

                prompt = (
                    f"Analyze the location query: '{raw}'.\n"
                    f"Is this a real, recognized city, town, island, national park, or travel destination on Earth?\n"
                    f"If it is random gibberish (such as 'dg', 'vuvv', 'xyz', 'asdf'), set is_real_location=false."
                )
                system = "You are a geographic verification engine. Audit whether locations exist."
                check = await llm_service.generate_structured(prompt, system, LLMLocationCheck)
                if check:
                    if check.is_real_location and check.canonical_name:
                        return LocationVerificationResult(
                            is_valid=True,
                            canonical_name=check.canonical_name,
                            country=check.country,
                        )
                    else:
                        return LocationVerificationResult(
                            is_valid=False,
                            error_message=f"'{raw}' is not a recognized travel destination or city ({check.explanation}).",
                        )
            except Exception as e:
                logger.debug(f"LLM location verification failed: {e}")

        # If both fail, reject the location
        return LocationVerificationResult(
            is_valid=False,
            error_message=f"Could not verify '{raw}' as a recognized city or destination on Earth. Please enter a valid location.",
        )


location_verifier = LocationVerifier()
