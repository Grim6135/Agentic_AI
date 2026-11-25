"""Groq chat completions for CrewAI's text-based task and tool protocol."""
import time
import httpx
from crewai import BaseLLM


class GroqChat(BaseLLM):
    def __init__(self, model, api_key):
        super().__init__(model=model, temperature=0)
        self._api_key = api_key

    def supports_function_calling(self):
        return False

    def supports_stop_words(self):
        return False

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        model = self.model.removeprefix("groq/")
        payload = {"model": model, "messages": [{"role": m["role"], "content": m["content"]} for m in messages], "temperature": 0}
        if model.startswith("openai/gpt-oss-"):
            payload["reasoning_effort"] = "low"
        # CrewAI interprets textual Action/Action Input pairs and runs tools locally.
        payload["messages"].insert(0, {"role": "system", "content": "Answer in plain text using the format requested. For a tool, write plain text Action and Action Input lines. Never emit an API function call. For Final Answer, include just the requested output."})
        payload["max_completion_tokens"] = 2400 if "Itinerary Specialist" in str(messages[0]) else 800
        headers = {"Authorization": "Bearer " + self._api_key}
        url = "https://api.groq.com/openai/v1/chat/completions"
        for attempt in range(2):
            response = httpx.post(url, headers=headers, json=payload, timeout=35)
            if response.status_code != 429 or attempt:
                break
            try:
                delay = float(response.headers.get("retry-after", "3"))
            except ValueError:
                delay = 3
            if delay > 45:
                break
            time.sleep(max(1, delay + 1))
        if response.is_error:
            # Retain only the provider status and a machine-readable code, never prompt contents.
            import re
            detail = response.json().get("error", {})
            code = str(detail.get("code") or detail.get("type") or "unknown")
            error = RuntimeError("Groq rejected itinerary request")
            error.status_code = response.status_code
            error.provider_code = code if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", code) else "unknown"
            raise error
        return response.json()["choices"][0]["message"]["content"]
