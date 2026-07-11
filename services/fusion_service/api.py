"""Fusion REST and WebSocket endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from services.fusion_service.models import (
    ActivityRecord,
    EventRecord,
    EventsResponse,
    FusionStatusResponse,
    TimelineResponse,
    TrendBucket,
    TrendsResponse,
)
from services.fusion_service.runtime import FusionMQTTDependency, run_blocking
from shared.labels import CANONICAL_ACTIVITIES


def _range_bounds(from_ts: datetime | None, to_ts: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    end = to_ts or now
    start = from_ts or end - timedelta(hours=24)
    for name, value in (("from", start), ("to", end)):
        if value.tzinfo is None or value.utcoffset() is None or value.utcoffset() != timedelta(0):
            raise HTTPException(status_code=422, detail=f"{name} must be timezone-aware UTC")
    if start > end:
        raise HTTPException(status_code=422, detail="from must not be after to")
    return start.astimezone(UTC), end.astimezone(UTC)


def _record(model: type[Any], value: dict[str, Any]) -> Any:
    return model.model_validate(value)


def _timeline_records(
    rows: list[dict[str, Any]], end: datetime, max_interval_seconds: float
) -> list[ActivityRecord]:
    """Attach bounded durations without treating offline gaps as activity."""

    records: list[ActivityRecord] = []
    for index, row in enumerate(rows):
        next_ts = rows[index + 1]["ts"] if index + 1 < len(rows) else end
        duration = max(
            0.0,
            min((next_ts - row["ts"]).total_seconds(), max_interval_seconds),
        )
        records.append(ActivityRecord.model_validate({**row, "duration_seconds": duration}))
    return records


def create_router(runtime: FusionMQTTDependency) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status", response_model=FusionStatusResponse)
    async def status() -> FusionStatusResponse:
        return runtime.status()

    @router.get("/api/timeline", response_model=TimelineResponse)
    async def timeline(
        from_ts: datetime | None = Query(default=None, alias="from"),  # noqa: B008
        to_ts: datetime | None = Query(default=None, alias="to"),  # noqa: B008
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> TimelineResponse:
        start, end = _range_bounds(from_ts, to_ts)
        limit = min(limit, runtime.settings.api_max_limit)
        try:
            rows = await run_blocking(runtime.activity_repository.between, start, end, limit)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="timeline persistence unavailable") from exc
        return TimelineResponse(
            items=_timeline_records(
                rows,
                end,
                max(runtime.settings.fusion_interval, 0.1) * 2,
            ),
            count=len(rows),
        )

    @router.get("/api/events", response_model=EventsResponse)
    async def events(
        from_ts: datetime | None = Query(default=None, alias="from"),  # noqa: B008
        to_ts: datetime | None = Query(default=None, alias="to"),  # noqa: B008
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> EventsResponse:
        start, end = _range_bounds(from_ts, to_ts)
        limit = min(limit, runtime.settings.api_max_limit)
        try:
            rows = await run_blocking(runtime.event_repository.between, start, end, limit)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="event persistence unavailable") from exc
        return EventsResponse(
            items=[_record(EventRecord, row) for row in rows],
            count=len(rows),
        )

    @router.get("/api/events/active-critical", response_model=EventRecord | None)
    async def active_critical_event() -> EventRecord | None:
        try:
            row = await run_blocking(runtime.event_repository.latest_unacknowledged_critical)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="event persistence unavailable") from exc
        return _record(EventRecord, row) if row else None

    @router.get("/api/trends", response_model=TrendsResponse)
    async def trends(
        period: str = Query(default="24h", min_length=2, max_length=8),
    ) -> TrendsResponse:
        periods = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        try:
            duration = periods[period.strip().lower()]
        except KeyError as exc:
            raise HTTPException(
                status_code=422,
                detail="period must be one of 1h, 24h, 7d, 30d",
            ) from exc
        end = datetime.now(UTC)
        start = end - duration
        try:
            rows = await run_blocking(
                runtime.activity_repository.trends,
                start,
                end,
                max(runtime.settings.fusion_interval, 0.1) * 2,
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail="trend persistence unavailable") from exc
        by_activity = {str(row["activity"]): row for row in rows}
        buckets = [
            TrendBucket(
                activity=activity,
                count=int(by_activity.get(activity, {}).get("count", 0)),
                duration_seconds=float(by_activity.get(activity, {}).get("duration_seconds", 0.0)),
            )
            for activity in CANONICAL_ACTIVITIES
        ]
        return TrendsResponse(
            period=period.strip().lower(),
            **{"from": start, "to": end},
            activities=buckets,
            total_duration_seconds=sum(bucket.duration_seconds for bucket in buckets),
        )

    @router.post("/api/events/{event_id}/ack", response_model=EventRecord)
    async def acknowledge(event_id: int) -> EventRecord:
        if event_id < 1:
            raise HTTPException(status_code=422, detail="event id must be positive")
        try:
            exists = await run_blocking(runtime.event_repository.acknowledge, event_id)
            row = await run_blocking(runtime.event_repository.get, event_id)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="event persistence unavailable") from exc
        if not exists or row is None:
            raise HTTPException(status_code=404, detail="event not found")
        return _record(EventRecord, row)

    @router.websocket("/ws")
    async def websocket(websocket: WebSocket) -> None:
        client_id = await runtime.websocket_hub.connect(websocket)
        try:
            while True:
                # The client does not need to send commands; receiving keeps
                # disconnects observable and prevents dead sockets lingering.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await runtime.websocket_hub.disconnect(client_id)

    return router
