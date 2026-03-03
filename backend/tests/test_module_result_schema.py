from datetime import datetime, timedelta, timezone
import unittest

from backend.schemas.module_result import (
    SCHEMA_VERSION,
    SchemaValidationError,
    is_schema_compatible,
    validate_before_publish,
)


class ModuleResultSchemaTests(unittest.TestCase):
    def _valid_payload(self):
        started = datetime.now(timezone.utc)
        completed = started + timedelta(seconds=2)
        return {
            "module": "static-analyzer",
            "status": "completed",
            "score": 91.2,
            "findings": [
                {
                    "severity": "high",
                    "category": "security",
                    "evidence": "Unsanitized input in handler",
                    "recommendation": "Add server-side input validation",
                }
            ],
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "trace_id": "trace-abc-123",
            "schema_version": SCHEMA_VERSION,
        }

    def test_validate_before_publish_accepts_valid_payload(self):
        payload = self._valid_payload()
        validated = validate_before_publish(payload)
        self.assertEqual(validated["status"], "completed")

    def test_failed_status_requires_error_envelope(self):
        payload = self._valid_payload()
        payload["status"] = "failed"
        with self.assertRaises(SchemaValidationError):
            validate_before_publish(payload)

    def test_failed_status_accepts_error_envelope(self):
        payload = self._valid_payload()
        payload["status"] = "failed"
        payload["error"] = {
            "code": "TIMEOUT",
            "message": "Module exceeded execution deadline",
            "details": {"timeout_seconds": 30},
            "retryable": True,
        }
        validated = validate_before_publish(payload)
        self.assertIn("error", validated)

    def test_unknown_top_level_field_is_rejected(self):
        payload = self._valid_payload()
        payload["extra"] = "not-allowed"
        with self.assertRaises(SchemaValidationError):
            validate_before_publish(payload)

    def test_schema_compatibility_major_version(self):
        self.assertTrue(is_schema_compatible("1.4.0"))
        self.assertFalse(is_schema_compatible("2.0.0"))


if __name__ == "__main__":
    unittest.main()
