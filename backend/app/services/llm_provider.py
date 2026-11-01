"""
TRIPPY Backend — Configurable LLM Provider

Provides a unified interface for invoking either Google Gemini or OpenAI
with structured JSON generation. Keeps credentials server-side.
Gracefully handles provider errors, timeouts, and invalid outputs
by falling back to deterministic processing without crashing.
"""

import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger("trippy.llm")

T = TypeVar("T", bound=BaseModel)


class LLMProviderService:
    """Configurable client for Gemini and OpenAI models."""

    def __init__(self):
        self.provider = settings.ai_provider.lower()
        self.api_key = settings.ai_api_key
        self.enabled = settings.ai_enabled and bool(self.api_key.strip())
        self.timeout = settings.ai_timeout_seconds

        # Select model name
        if settings.ai_model.strip():
            self.model = settings.ai_model.strip()
        elif self.provider == "gemini":
            self.model = "gemini-1.5-flash"
        else:
            self.model = "gpt-4o-mini"

    def is_available(self) -> bool:
        """Returns True if AI provider is enabled and configured with an API key."""
        return self.enabled

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str,
        schema_cls: Type[T],
    ) -> Optional[T]:
        """
        Attempts to generate a structured JSON response matching schema_cls.
        Returns None on any error, timeout, or failure so callers fall back cleanly.
        """
        if not self.is_available():
            return None

        try:
            if self.provider == "gemini":
                return await self._call_gemini(prompt, system_instruction, schema_cls)
            elif self.provider == "openai":
                return await self._call_openai(prompt, system_instruction, schema_cls)
            else:
                logger.warning(f"Unknown AI provider configured: {self.provider}")
                return None
        except httpx.TimeoutException:
            logger.warning(f"LLM request timed out after {self.timeout}s.")
            return None
        except httpx.HTTPError as err:
            logger.warning(f"LLM HTTP communication error: {err}")
            return None
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(f"Failed to validate LLM response into {schema_cls.__name__}: {err}")
            return None
        except Exception as err:
            logger.warning(f"Unexpected error during LLM generation: {err}")
            return None

    async def _call_gemini(
        self,
        prompt: str,
        system_instruction: str,
        schema_cls: Type[T],
    ) -> Optional[T]:
        """Calls the Gemini REST API with JSON response enforcement."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Extract generated content
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None
            text = parts[0].get("text", "")
            parsed = json.loads(text)
            return schema_cls.model_validate(parsed)

    async def _call_openai(
        self,
        prompt: str,
        system_instruction: str,
        schema_cls: Type[T],
    ) -> Optional[T]:
        """Calls the OpenAI Chat Completions API with json_object enforcement."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"{system_instruction}\nYou MUST respond with valid JSON matching {schema_cls.__name__}."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            if not choices:
                return None
            text = choices[0].get("message", {}).get("content", "")
            parsed = json.loads(text)
            return schema_cls.model_validate(parsed)


llm_service = LLMProviderService()
