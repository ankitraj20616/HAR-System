import json
import logging
import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from shared.config import Settings
from shared.logging import JsonFormatter, configure_logging
from shared.schemas import MESSAGE_SCHEMA_VERSION


class SettingsTests(unittest.TestCase):
    def test_settings_parse_environment(self):
        environment = {
            "MQTT_HOST": "broker",
            "MQTT_PORT": "2883",
            "DATABASE_URL": "postgresql://user:pass@database:5432/har",
            "LOG_LEVEL": "debug",
            "FUSION_PORT": "9001",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings()
        self.assertEqual(settings.mqtt_host, "broker")
        self.assertEqual(settings.mqtt_port, 2883)
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.fusion_port, 9001)
        self.assertEqual(settings.message_schema_version, MESSAGE_SCHEMA_VERSION)

    def test_invalid_port_log_level_and_database_are_rejected(self):
        for values in (
            {"mqtt_port": 70000},
            {"log_level": "verbose"},
            {"database_url": "sqlite:///har.db"},
            {"database_url": "postgresql://localhost"},
            {"database_url": "postgresql://localhost:70000/har"},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                Settings(**values)

    def test_validation_text_does_not_expose_database_credentials(self):
        secret = "do-not-log-this-password"
        with self.assertRaises(ValidationError) as caught:
            Settings(database_url=f"postgresql://har:{secret}@localhost")
        self.assertNotIn(secret, str(caught.exception))


class LoggingTests(unittest.TestCase):
    def test_formatter_emits_required_structured_fields(self):
        record = logging.LogRecord(
            "test", logging.WARNING, __file__, 1, "broker unavailable", (), None
        )
        record.event = "dependency.degraded"
        record.correlation_id = "request-12"
        payload = json.loads(JsonFormatter("sensor-service").format(record))
        self.assertEqual(payload["level"], "warning")
        self.assertEqual(payload["service"], "sensor-service")
        self.assertEqual(payload["event"], "dependency.degraded")
        self.assertEqual(payload["message"], "broker unavailable")
        self.assertEqual(payload["correlation_id"], "request-12")
        self.assertTrue(payload["ts"].endswith("Z"))

    def test_configure_logging_is_idempotent_and_normalizes_level(self):
        root = logging.getLogger()
        original_level = root.level
        try:
            logger = configure_logging(" fusion-service ", " warning ")
            configure_logging("fusion-service", "WARNING")
            har_handlers = [
                handler for handler in root.handlers if getattr(handler, "_har_handler", False)
            ]
            self.assertEqual(logger.name, "fusion-service")
            self.assertEqual(root.level, logging.WARNING)
            self.assertEqual(len(har_handlers), 1)
        finally:
            for handler in list(root.handlers):
                if getattr(handler, "_har_handler", False):
                    root.removeHandler(handler)
                    handler.close()
            root.setLevel(original_level)

    def test_logging_rejects_invalid_service_and_level(self):
        with self.assertRaises(ValueError):
            JsonFormatter("  ")
        with self.assertRaises(ValueError):
            configure_logging("sensor-service", "WARN")


if __name__ == "__main__":
    unittest.main()
