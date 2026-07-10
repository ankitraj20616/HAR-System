import unittest
from datetime import UTC, datetime

from shared.db import (
    SCHEMA_SQL,
    ActivityRepository,
    EventRepository,
    FeedbackRepository,
    acknowledge_event,
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


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = []
        self.rowcount = connection.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.connection.executions.append((query, params))
        if self.connection.execute_error is not None:
            raise self.connection.execute_error

    def fetchone(self):
        return self.connection.fetchone

    def fetchall(self):
        return self.connection.fetchall


class FakeConnection:
    def __init__(
        self,
        fetchone=(True,),
        fetchall=None,
        rowcount=1,
        execute_error=None,
        description=None,
    ):
        self.fetchone = fetchone
        self.fetchall = fetchall or []
        self.rowcount = rowcount
        self.execute_error = execute_error
        self.description = description or []
        self.executions = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        cursor = FakeCursor(self)
        cursor.description = self.description
        return cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class DatabaseTests(unittest.TestCase):
    def test_schema_is_repeatable_and_contains_required_constraints(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS activity_timeline", SCHEMA_SQL)
        self.assertIn("CREATE TABLE IF NOT EXISTS events", SCHEMA_SQL)
        self.assertIn("CREATE TABLE IF NOT EXISTS feedback", SCHEMA_SQL)
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_feedback_ts", SCHEMA_SQL)
        self.assertIn("confidence >= 0 AND confidence <= 1", SCHEMA_SQL)
        self.assertIn("jsonb_typeof(evidence) = 'object'", SCHEMA_SQL)

        connection = FakeConnection()
        initialize_database(connection)
        initialize_database(connection)
        self.assertEqual(connection.commits, 2)
        self.assertEqual(connection.executions[0][0], SCHEMA_SQL)

    def test_readiness_returns_false_instead_of_leaking_connection_error(self):
        def broken_connection(_url):
            raise ConnectionError("database is offline")

        self.assertFalse(is_database_ready("postgresql://x", broken_connection))
        self.assertTrue(is_database_ready(FakeConnection()))

    def test_readiness_requires_the_complete_schema_and_closes_owned_connection(self):
        incomplete = FakeConnection(fetchone=(False,))

        self.assertFalse(is_database_ready("postgresql://x", lambda _url: incomplete))
        self.assertTrue(incomplete.closed)
        query, params = incomplete.executions[0]
        self.assertIn("to_regclass('activity_timeline')", query)
        self.assertIn("to_regclass('idx_feedback_ts')", query)
        self.assertIsNone(params)

    def test_insert_activity_uses_parameterized_query_and_commits(self):
        connection = FakeConnection(fetchone=(42,))
        activity = FusedActivity(
            ts="2026-06-20T10:00:00Z",
            activity="WALKING",
            confidence=0.9,
            contributors={"sensor": "WALKING", "video": "WALKING"},
        )
        self.assertEqual(insert_activity(connection, activity), 42)
        query, params = connection.executions[0]
        self.assertIn("RETURNING id", query)
        self.assertIn("%s", query)
        self.assertEqual(params[1], "WALKING")
        self.assertEqual(connection.commits, 1)

    def test_all_record_types_insert_json_safely_and_commit(self):
        timestamp = datetime(2026, 6, 20, 10, tzinfo=UTC)
        event_connection = FakeConnection(fetchone=(7,))
        event = HAREvent(
            ts=timestamp,
            type="FALL",
            severity="critical",
            confidence=0.93,
            evidence={"orientation": "horizontal"},
        )
        self.assertEqual(insert_event(event_connection, event), 7)
        event_query, event_params = event_connection.executions[0]
        self.assertIn("%s::jsonb", event_query)
        self.assertEqual(event_params[-1], '{"orientation": "horizontal"}')

        feedback_connection = FakeConnection(fetchone=(8,))
        feedback = Feedback(
            ts=timestamp,
            mode="alert",
            headline="Possible fall detected",
            detail="A possible fall was detected.",
            severity="critical",
            recommendations=["Check on the patient."],
            disclaimer="Not a medical diagnosis.",
        )
        self.assertEqual(insert_feedback(feedback_connection, feedback), 8)
        feedback_query, feedback_params = feedback_connection.executions[0]
        self.assertIn("%s::jsonb", feedback_query)
        self.assertIn('"recommendations": ["Check on the patient."]', feedback_params[-1])
        self.assertEqual(event_connection.commits, 1)
        self.assertEqual(feedback_connection.commits, 1)

    def test_insert_failure_rolls_back_without_committing(self):
        connection = FakeConnection(execute_error=RuntimeError("write failed"))
        activity = FusedActivity(
            ts="2026-06-20T10:00:00Z",
            activity="WALKING",
            confidence=0.9,
            contributors={"sensor": "WALKING"},
        )

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            insert_activity(connection, activity)
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_recent_queries_are_parameterized_and_return_named_columns(self):
        columns_by_reader = (
            (
                get_recent_activities,
                ["id", "ts", "activity", "confidence", "sensor_label", "video_label"],
                [1, "2026-06-20T10:00:00Z", "WALKING", 0.9, "WALKING", None],
            ),
            (
                get_recent_events,
                ["id", "ts", "type", "severity", "confidence", "evidence", "acknowledged"],
                [2, "2026-06-20T10:00:00Z", "FALL", "critical", 0.9, {}, False],
            ),
            (
                get_recent_feedback,
                ["id", "ts", "mode", "headline", "detail", "severity", "payload"],
                [3, "2026-06-20T10:00:00Z", "alert", "Fall", "Detail", "critical", {}],
            ),
        )
        for reader, columns, row in columns_by_reader:
            connection = FakeConnection(
                fetchall=[tuple(row)], description=[(column,) for column in columns]
            )
            self.assertEqual(reader(connection, 5), [dict(zip(columns, row, strict=True))])
            query, params = connection.executions[0]
            self.assertIn("ORDER BY ts DESC, id DESC LIMIT %s", query)
            self.assertEqual(params, (5,))

        for invalid_limit in (0, 1001):
            with self.assertRaises(ValueError):
                get_recent_feedback(FakeConnection(), invalid_limit)
        with self.assertRaises(TypeError):
            get_recent_feedback(FakeConnection(), True)

    def test_event_acknowledgement_is_idempotent(self):
        changed = FakeConnection(rowcount=1)
        unchanged = FakeConnection(rowcount=0)
        self.assertTrue(acknowledge_event(changed, 10))
        self.assertFalse(acknowledge_event(unchanged, 10))
        self.assertEqual(changed.commits, 1)
        with self.assertRaises(ValueError):
            acknowledge_event(changed, 0)

    def test_repositories_use_injected_connections_and_close_them(self):
        activity_connection = FakeConnection(fetchone=(1,))
        event_connection = FakeConnection(fetchone=(2,))
        feedback_connection = FakeConnection(fetchone=(3,))
        timestamp = "2026-06-20T10:00:00Z"

        activity_repository = ActivityRepository(
            "postgresql://test", lambda _url: activity_connection
        )
        event_repository = EventRepository("postgresql://test", lambda _url: event_connection)
        feedback_repository = FeedbackRepository(
            "postgresql://test", lambda _url: feedback_connection
        )

        activity_repository.add(
            FusedActivity(
                ts=timestamp,
                activity="WALKING",
                confidence=0.9,
                contributors={"sensor": "WALKING"},
            )
        )
        event_repository.add(
            HAREvent(
                ts=timestamp,
                type="FALL",
                severity="critical",
                confidence=0.9,
                evidence={},
            )
        )
        feedback_repository.add(
            Feedback(
                ts=timestamp,
                mode="alert",
                headline="Fall",
                detail="Possible fall.",
                severity="critical",
                recommendations=[],
                disclaimer="Not medical advice.",
            )
        )

        self.assertTrue(activity_connection.closed)
        self.assertTrue(event_connection.closed)
        self.assertTrue(feedback_connection.closed)


if __name__ == "__main__":
    unittest.main()
