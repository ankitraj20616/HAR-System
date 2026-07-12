"""Dashboard-facing feedback REST and WebSocket endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from services.feedback_service.models import GenerateRequest, GenerationResponse
from services.feedback_service.runtime import FeedbackRuntime
from shared.schemas import Feedback


def create_router(runtime: FeedbackRuntime) -> APIRouter:
    router = APIRouter()

    @router.get("/api/feedback/latest", response_model=Feedback | None)
    async def latest_feedback() -> Feedback | None:
        try:
            return await runtime.latest()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="feedback persistence unavailable") from exc

    @router.post("/api/feedback/generate", response_model=GenerationResponse)
    async def generate_feedback(request: GenerateRequest) -> GenerationResponse:
        default_from, default_to = runtime.default_range()
        if request.period:
            duration = {
                "1h": timedelta(hours=1),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30),
            }[request.period]
            to_ts = datetime.now(UTC)
            from_ts = to_ts - duration
        else:
            from_ts = request.from_ts or default_from
            to_ts = request.to_ts or default_to
        if from_ts > to_ts:
            raise HTTPException(status_code=422, detail="from must not be after to")
        if to_ts > datetime.now(UTC) + timedelta(minutes=1):
            raise HTTPException(status_code=422, detail="to must not be in the future")
        if to_ts - from_ts > timedelta(days=runtime.settings.feedback_api_max_period_days):
            raise HTTPException(status_code=422, detail="requested period is too large")
        try:
            result, replay = await runtime.generate_period(
                request.mode, from_ts, to_ts, request.request_id
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="feedback provider unavailable") from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="feedback generation unavailable") from exc
        payload = result.feedback.model_dump(mode="json")
        payload.update(
            fallback=result.fallback_used,
            provider_status=result.provider_status,
            idempotent_replay=replay,
        )
        return GenerationResponse.model_validate(payload)

    @router.websocket("/ws")
    async def websocket(socket: WebSocket) -> None:
        client_id = await runtime.websocket_hub.connect(socket)
        try:
            while True:
                await socket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await runtime.websocket_hub.disconnect(client_id)

    return router
