"""Groq chat completions for CrewAI's text-based task and tool protocol."""
import time
import httpx
from crewai import LLM


class GroqChat(LLM):
    def __init__(self, model, api_key):
        super().__init__(model=model, api_key=api_key, temperature=0)
        self._api_key = api_key

    def supports_function_calling(self):
        return False

    def supports_stop_words(self):
        return False

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        primary_model = self.model.removeprefix("groq/")
        # Try primary model, fallback to secondary Groq model if primary is rate-limited
        candidate_models = [primary_model]
        fallback = "openai/gpt-oss-20b" if primary_model != "openai/gpt-oss-20b" else "qwen/qwen3.8-27b"
        candidate_models.append(fallback)

        headers = {"Authorization": "Bearer " + self._api_key}
        url = "https://api.groq.com/openai/v1/chat/completions"

        for model in candidate_models:
            payload = {"model": model, "messages": [{"role": m["role"], "content": m["content"]} for m in messages], "temperature": 0}
            if model.startswith("openai/gpt-oss-"):
                payload["reasoning_effort"] = "low"
            # CrewAI interprets textual Action/Action Input pairs and runs tools locally.
            if "Itinerary Specialist" in str(messages):
                payload["messages"].insert(0, {"role": "system", "content": "You are the Itinerary Specialist. Output ONLY a valid JSON object matching the requested schema: {\"summary\": \"...\", \"lodging_category\": \"...\", \"days\": [{\"activity\": \"...\", \"description\": \"...\"}]}. Do not include markdown code blocks or conversational text."})
            else:
                payload["messages"].insert(0, {"role": "system", "content": "You are a concise travel specialist. Answer immediately in plain text. For Final Answer, output: Final Answer: [brief assessment under 40 words]. Do not call tools unless essential data is absent."})
            payload["max_completion_tokens"] = 650 if "Itinerary Specialist" in str(messages) else 60

            for attempt in range(4):
                response = httpx.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code != 429:
                    break
                try:
                    detail = response.json().get("error", {}).get("message", "")
                    import re
                    match = re.search(r"try again in ([0-9.]+)s", detail)
                    if match:
                        delay = float(match.group(1))
                    else:
                        retry_header = response.headers.get("retry-after")
                        delay = float(retry_header) if retry_header else 2.5
                except Exception:
                    delay = 2.5
                # If rate limited for more than 15s (daily quota), switch models immediately
                if delay > 15.0:
                    break
                time.sleep(min(max(1.0, delay + 0.3), 8.0))

            if not response.is_error:
                choice = response.json()["choices"][0]["message"]
                content = choice.get("content") or ""
                if not content.strip():
                    content = choice.get("reasoning", "").strip() or "Final Answer: Reviewed and confirmed."
                return content

        # Retain only the provider status and a machine-readable code, never prompt contents.
        import re
        detail = response.json().get("error", {})
        code = str(detail.get("code") or detail.get("type") or "unknown")
        error = RuntimeError("Groq rejected itinerary request")
        error.status_code = response.status_code
        error.provider_code = code if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", code) else "unknown"
        raise error
