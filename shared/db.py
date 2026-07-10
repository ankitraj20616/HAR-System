"""PostgreSQL initialization and persistence helpers.

The functions accept an existing DB-API connection, which keeps unit tests and
service dependency injection simple. Repository classes additionally manage a
connection from a PostgreSQL URL for normal runtime use.
"""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .schemas import Feedback, FusedActivity, HAREvent

SCHEMA_SQL = (Path(__file__).parent / "sql" / "001_init.sql").read_text(encoding="utf-8")
Connection = Any
ConnectionTarget = str | Connection
ConnectionFactory = Callable[[str], Connection]

_SCHEMA_READINESS_SQL = """
SELECT
    to_regclass('activity_timeline') IS NOT NULL
    AND to_regclass('events') IS NOT NULL
    AND to_regclass('feedback') IS NOT NULL
    AND to_regclass('idx_timeline_ts') IS NOT NULL
    AND to_regclass('idx_events_ts') IS NOT NULL
    AND to_regclass('idx_feedback_ts') IS NOT NULL
"""


def connect(database_url: str) -> Connection:
    """Open a PostgreSQL connection, importing the driver only when needed."""

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on runtime packaging
        raise RuntimeError("PostgreSQL support requires the 'psycopg[binary]' package") from exc
    normalized_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg.connect(normalized_url)


@contextmanager
def _connection_for(
    target: ConnectionTarget, connection_factory: ConnectionFactory = connect
) -> Iterator[Connection]:
    owns_connection = isinstance(target, str)
    connection = connection_factory(target) if owns_connection else target
    try:
        yield connection
    finally:
        if owns_connection:
            connection.close()


def initialize_database(
    target: ConnectionTarget, connection_factory: ConnectionFactory = connect
) -> None:
    """Apply the repeatable schema and indexes in one transaction."""

    with _connection_for(target, connection_factory) as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def is_database_ready(
    target: ConnectionTarget, connection_factory: ConnectionFactory = connect
) -> bool:
    """Return whether PostgreSQL and the complete Milestone 1 schema are ready.

    Dependency health must not report a fresh but uninitialized PostgreSQL
    instance as ready.  ``to_regclass`` makes the check cheap and returns NULL
    instead of raising when a required relation is absent.
    """

    try:
        with (
            _connection_for(target, connection_factory) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute(_SCHEMA_READINESS_SQL)
            return cursor.fetchone() == (True,)
    except Exception:
        return False


def _insert_returning_id(connection: Connection, query: str, params: tuple[Any, ...]) -> int:
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("insert did not return an id")
            record_id = int(row[0])
        connection.commit()
        return record_id
    except Exception:
        connection.rollback()
        raise


def insert_activity(connection: Connection, activity: FusedActivity) -> int:
    return _insert_returning_id(
        connection,
        """
        INSERT INTO activity_timeline
            (ts, activity, confidence, sensor_label, video_label)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            activity.ts,
            activity.activity,
            activity.confidence,
            activity.contributors.sensor,
            activity.contributors.video,
        ),
    )


def insert_event(connection: Connection, event: HAREvent) -> int:
    return _insert_returning_id(
        connection,
        """
        INSERT INTO events (ts, type, severity, confidence, evidence)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id
        """,
        (event.ts, event.type, event.severity, event.confidence, json.dumps(event.evidence)),
    )


def insert_feedback(connection: Connection, feedback: Feedback) -> int:
    payload = (
        feedback.model_dump(mode="json")
        if hasattr(feedback, "model_dump")
        else json.loads(feedback.json())
    )
    return _insert_returning_id(
        connection,
        """
        INSERT INTO feedback (ts, mode, headline, detail, severity, payload)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id
        """,
        (
            feedback.ts,
            feedback.mode,
            feedback.headline,
            feedback.detail,
            feedback.severity,
            json.dumps(payload),
        ),
    )


def _fetch_dicts(
    connection: Connection, query: str, params: tuple[Any, ...]
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")


def get_recent_activities(connection: Connection, limit: int = 100) -> list[dict[str, Any]]:
    _validate_limit(limit)
    return _fetch_dicts(
        connection,
        """
        SELECT id, ts, activity, confidence, sensor_label, video_label
        FROM activity_timeline ORDER BY ts DESC, id DESC LIMIT %s
        """,
        (limit,),
    )


def get_recent_events(connection: Connection, limit: int = 100) -> list[dict[str, Any]]:
    _validate_limit(limit)
    return _fetch_dicts(
        connection,
        """
        SELECT id, ts, type, severity, confidence, evidence, acknowledged
        FROM events ORDER BY ts DESC, id DESC LIMIT %s
        """,
        (limit,),
    )


def get_recent_feedback(connection: Connection, limit: int = 100) -> list[dict[str, Any]]:
    """Return newest feedback first using deterministic ordering for equal timestamps."""

    _validate_limit(limit)
    return _fetch_dicts(
        connection,
        """
        SELECT id, ts, mode, headline, detail, severity, payload
        FROM feedback ORDER BY ts DESC, id DESC LIMIT %s
        """,
        (limit,),
    )


def acknowledge_event(connection: Connection, event_id: int) -> bool:
    if event_id < 1:
        raise ValueError("event_id must be positive")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE events SET acknowledged = TRUE WHERE id = %s AND acknowledged = FALSE",
                (event_id,),
            )
            changed = cursor.rowcount == 1
        connection.commit()
        return changed
    except Exception:
        connection.rollback()
        raise


class BaseRepository:
    def __init__(self, database_url: str, connection_factory: ConnectionFactory = connect) -> None:
        self.database_url = database_url
        self.connection_factory = connection_factory

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        with _connection_for(self.database_url, self.connection_factory) as connection:
            yield connection


class ActivityRepository(BaseRepository):
    def add(self, activity: FusedActivity) -> int:
        with self.connection() as connection:
            return insert_activity(connection, activity)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            return get_recent_activities(connection, limit)


class EventRepository(BaseRepository):
    def add(self, event: HAREvent) -> int:
        with self.connection() as connection:
            return insert_event(connection, event)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            return get_recent_events(connection, limit)

    def acknowledge(self, event_id: int) -> bool:
        with self.connection() as connection:
            return acknowledge_event(connection, event_id)


class FeedbackRepository(BaseRepository):
    def add(self, feedback: Feedback) -> int:
        with self.connection() as connection:
            return insert_feedback(connection, feedback)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            return get_recent_feedback(connection, limit)
