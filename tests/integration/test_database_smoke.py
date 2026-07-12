"""Opt-in PostgreSQL smoke test for the Milestone 1 persistence path."""

import os
from datetime import UTC, datetime

import pytest

from shared.db import (
    connect,
    get_recent_activities,
    get_recent_events,
    get_recent_feedback,
    initialize_database,
    insert_activity,
    insert_event,
    insert_feedback,
    is_database_ready,
)
from shared.schemas import Feedback, FusedActivity, HAREvent


def test_postgresql_initialize_insert_and_read_smoke() -> None:
    """Exercise real DDL and all repositories when a test database is supplied."""

    database_url = os.getenv("HAR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set HAR_TEST_DATABASE_URL to run the PostgreSQL smoke test")

    # Running initialization twice is part of the milestone acceptance criteria.
    initialize_database(database_url)
    initialize_database(database_url)
    assert is_database_ready(database_url)

    timestamp = datetime.now(UTC)
    connection = connect(database_url)
    inserted: dict[str, int] = {}
    try:
        inserted["activity"] = insert_activity(
            connection,
            FusedActivity(
                ts=timestamp,
                activity="WALKING",
                confidence=0.91,
                contributors={"sensor": "WALKING", "video": "WALKING"},
            ),
        )
        inserted["event"] = insert_event(
            connection,
            HAREvent(
                ts=timestamp,
                type="FALL",
                severity="critical",
                confidence=0.92,
                evidence={"test": True},
            ),
        )
        inserted["feedback"] = insert_feedback(
            connection,
            Feedback(
                ts=timestamp,
                mode="alert",
                headline="Database smoke test",
                detail="This record verifies PostgreSQL persistence.",
                severity="critical",
                recommendations=["Ignore this test record."],
                disclaimer="This is an automated test, not medical advice.",
            ),
        )

        assert any(row["id"] == inserted["activity"] for row in get_recent_activities(connection))
        assert any(row["id"] == inserted["event"] for row in get_recent_events(connection))
        assert any(row["id"] == inserted["feedback"] for row in get_recent_feedback(connection))
    finally:
        # The environment variable deliberately opts into mutation, but leave
        # the supplied test database clean after either success or failure.
        if inserted:
            with connection.cursor() as cursor:
                if "activity" in inserted:
                    cursor.execute(
                        "DELETE FROM activity_timeline WHERE id = %s", (inserted["activity"],)
                    )
                if "event" in inserted:
                    cursor.execute("DELETE FROM events WHERE id = %s", (inserted["event"],))
                if "feedback" in inserted:
                    cursor.execute("DELETE FROM feedback WHERE id = %s", (inserted["feedback"],))
            connection.commit()
        connection.close()
