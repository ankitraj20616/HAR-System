"""LLM provider abstraction and local Ollama adapter."""

from __future__ import annotations

import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.feedback_service.models import FeedbackContent

SYSTEM_PROMPT = """You summarize recorded physical activity for a caregiver.
Use concise plain language. Never diagnose or imply a diagnosis. Use only facts in the supplied
JSON digest: do not invent identity, vital signs, causes, injuries, or missing activity. Recommend
only safe general actions and contacting a qualified professional for medical concerns. Always
include a disclaimer saying this automated assistive output is not a medical diagnosis.
Return JSON only with headline, detail, severity (info|warning|critical), recommendations (1-5
strings), and disclaimer."""


class ProviderError(RuntimeError):
    pass


class FeedbackProvider(Protocol):
    def generate(self, mode: str, digest: dict[str, Any]) -> FeedbackContent: ...


class OllamaProvider:
    def __init__(self, host: str, model: str, timeout: float = 30.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, mode: str, digest: dict[str, Any]) -> FeedbackContent:
        prompt = f"Mode: {mode}\nSupplied factual digest:\n{json.dumps(digest, sort_keys=True)}"
        body = json.dumps(
            {
                "model": self.model,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "format": FeedbackContent.model_json_schema(),
                "options": {"temperature": 0.1},
            }
        ).encode("utf-8")
        request = Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                envelope = json.loads(response.read().decode("utf-8"))
            raw = envelope["response"]
            payload = json.loads(raw) if isinstance(raw, str) else raw
            return FeedbackContent.model_validate(payload)
        except (HTTPError, URLError, TimeoutError, KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"Ollama generation failed ({type(exc).__name__})") from exc


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemma-4-26b-a4b-it", timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider")
        self.api_key = api_key
        # Use whatever model is specified in the config
        self.model = model
        self.timeout = timeout

    def generate(self, mode: str, digest: dict[str, Any]) -> FeedbackContent:
        prompt = f"Mode: {mode}\nSupplied factual digest:\n{json.dumps(digest, sort_keys=True)}"
        body = json.dumps(
            {
                "system_instruction": {"parts": {"text": SYSTEM_PROMPT}},
                "contents": {"parts": {"text": prompt}},
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            }
        ).encode("utf-8")
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                envelope = json.loads(response.read().decode("utf-8"))
            raw = envelope["candidates"][0]["content"]["parts"][0]["text"]
            payload = json.loads(raw) if isinstance(raw, str) else raw
            return FeedbackContent.model_validate(payload)
        except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"Gemini generation failed ({type(exc).__name__})") from exc
