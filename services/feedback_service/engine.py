"""Feedback orchestration: provider, repair, validation, and deterministic fallback."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import Any

from services.feedback_service.fallback import deterministic_feedback
from services.feedback_service.llm import FeedbackProvider
from services.feedback_service.models import FeedbackContent
from services.feedback_service.safety import validate_safety
from shared.schemas import Feedback


@dataclass(frozen=True)
class GenerationResult:
    feedback: Feedback
    fallback_used: bool
    provider_status: str


class FeedbackEngine:
    def __init__(self, provider: FeedbackProvider, *, fallback_enabled: bool = True) -> None:
        self.provider = provider
        self.fallback_enabled = fallback_enabled

    async def generate(self, mode: str, digest: dict[str, Any]) -> GenerationResult:
        last_error: Exception | None = None
        attempt_digest = digest
        for _attempt in range(2):
            try:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="feedback-llm")
                try:
                    content = await asyncio.get_running_loop().run_in_executor(
                        executor, partial(self.provider.generate, mode, attempt_digest)
                    )
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                if not isinstance(content, FeedbackContent):
                    content = FeedbackContent.model_validate(content)
                validate_safety(content, digest)
                return GenerationResult(self._wire(mode, content), False, "ok")
            except Exception as exc:
                last_error = exc
                attempt_digest = {
                    **digest,
                    "repair_instruction": (
                        "The prior response failed schema or safety validation. Return corrected "
                        "JSON using only the original digest facts and the required disclaimer."
                    ),
                }
        if not self.fallback_enabled:
            raise RuntimeError("feedback provider failed validation") from last_error
        content = deterministic_feedback(mode, digest)
        validate_safety(content, digest)
        return GenerationResult(self._wire(mode, content), True, "fallback")

    @staticmethod
    def _wire(mode: str, content: FeedbackContent) -> Feedback:
        return Feedback(ts=datetime.now(UTC), mode=mode, **content.model_dump())
