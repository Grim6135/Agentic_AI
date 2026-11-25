"""Groq chat completions for CrewAI's text-based task and tool protocol."""
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
        response = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": "Bearer " + self._api_key}, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
