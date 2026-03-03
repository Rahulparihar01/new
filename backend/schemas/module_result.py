"""Strict schema and boundary validation for analyzer module outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

SCHEMA_VERSION = "1.0.0"


class SchemaValidationError(ValueError):
    """Raised when a payload does not satisfy the module result schema."""


class ModuleStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Finding:
    severity: FindingSeverity
    category: str
    evidence: str
    recommendation: str

    def __post_init__(self) -> None:
        for field_name in ("category", "evidence", "recommendation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise SchemaValidationError(f"finding.{field_name} must be a non-empty string")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Finding":
        required = {"severity", "category", "evidence", "recommendation"}
        _ensure_exact_keys(payload, required, "finding")
        try:
            severity = FindingSeverity(payload["severity"])
        except ValueError as exc:
            allowed = ", ".join(item.value for item in FindingSeverity)
            raise SchemaValidationError(f"finding.severity must be one of: {allowed}") from exc

        return cls(
            severity=severity,
            category=str(payload["category"]),
            evidence=str(payload["evidence"]),
            recommendation=str(payload["recommendation"]),
        )

    def to_payload(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise SchemaValidationError("error.code must be a non-empty string")
        if not isinstance(self.message, str) or not self.message.strip():
            raise SchemaValidationError("error.message must be a non-empty string")
        if not isinstance(self.details, dict):
            raise SchemaValidationError("error.details must be an object")
        if not isinstance(self.retryable, bool):
            raise SchemaValidationError("error.retryable must be a boolean")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ErrorEnvelope":
        required = {"code", "message", "details", "retryable"}
        _ensure_exact_keys(payload, required, "error")
        return cls(
            code=str(payload["code"]),
            message=str(payload["message"]),
            details=dict(payload["details"]),
            retryable=bool(payload["retryable"]),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
        }


@dataclass(frozen=True, slots=True)
class ModuleResult:
    module: str
    status: ModuleStatus
    score: float
    findings: tuple[Finding, ...]
    started_at: datetime
    completed_at: datetime
    trace_id: str
    schema_version: str = SCHEMA_VERSION
    error: ErrorEnvelope | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or not self.module.strip():
            raise SchemaValidationError("module must be a non-empty string")
        if not isinstance(self.status, ModuleStatus):
            raise SchemaValidationError("status must be a valid ModuleStatus")
        if not isinstance(self.score, (int, float)):
            raise SchemaValidationError("score must be numeric")
        if not (0 <= float(self.score) <= 100):
            raise SchemaValidationError("score must be between 0 and 100")
        if not isinstance(self.findings, tuple):
            raise SchemaValidationError("findings must be a tuple of Finding objects")
        if not all(isinstance(item, Finding) for item in self.findings):
            raise SchemaValidationError("findings must contain only Finding objects")
        if not isinstance(self.started_at, datetime) or not isinstance(self.completed_at, datetime):
            raise SchemaValidationError("started_at and completed_at must be datetimes")
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise SchemaValidationError("started_at and completed_at must be timezone-aware")
        if self.completed_at < self.started_at:
            raise SchemaValidationError("completed_at must be greater than or equal to started_at")
        if not isinstance(self.trace_id, str) or not self.trace_id.strip():
            raise SchemaValidationError("trace_id must be a non-empty string")
        if not is_schema_compatible(self.schema_version):
            raise SchemaValidationError(
                f"schema_version '{self.schema_version}' is not compatible with expected {SCHEMA_VERSION}"
            )
        if self.status is ModuleStatus.FAILED and self.error is None:
            raise SchemaValidationError("error envelope is required when status is 'failed'")
        if self.status is not ModuleStatus.FAILED and self.error is not None:
            raise SchemaValidationError("error envelope is only valid when status is 'failed'")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ModuleResult":
        required = {
            "module",
            "status",
            "score",
            "findings",
            "started_at",
            "completed_at",
            "trace_id",
            "schema_version",
        }
        optional = {"error"}
        _ensure_exact_keys(payload, required | optional, "module_result", required_only=required)

        try:
            status = ModuleStatus(payload["status"])
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ModuleStatus)
            raise SchemaValidationError(f"status must be one of: {allowed}") from exc

        findings_raw = payload["findings"]
        if not isinstance(findings_raw, list):
            raise SchemaValidationError("findings must be an array")

        findings = tuple(Finding.from_payload(item) for item in findings_raw)
        error_payload = payload.get("error")
        error = ErrorEnvelope.from_payload(error_payload) if error_payload is not None else None

        return cls(
            module=str(payload["module"]),
            status=status,
            score=float(payload["score"]),
            findings=findings,
            started_at=_parse_iso8601(payload["started_at"], "started_at"),
            completed_at=_parse_iso8601(payload["completed_at"], "completed_at"),
            trace_id=str(payload["trace_id"]),
            schema_version=str(payload["schema_version"]),
            error=error,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "module": self.module,
            "status": self.status.value,
            "score": float(self.score),
            "findings": [finding.to_payload() for finding in self.findings],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "trace_id": self.trace_id,
            "schema_version": self.schema_version,
        }
        if self.error is not None:
            payload["error"] = self.error.to_payload()
        return payload


def is_schema_compatible(incoming_version: str, expected_version: str = SCHEMA_VERSION) -> bool:
    """Backward compatibility policy: same MAJOR versions are compatible for consumers."""
    try:
        incoming_major = int(incoming_version.split(".", maxsplit=1)[0])
        expected_major = int(expected_version.split(".", maxsplit=1)[0])
    except (ValueError, AttributeError, IndexError):
        return False
    return incoming_major == expected_major


def validate_before_publish(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate at module boundary before queue publish or stream emit."""
    return ModuleResult.from_payload(payload).to_payload()


def _parse_iso8601(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise SchemaValidationError(f"{field_name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SchemaValidationError(f"{field_name} must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise SchemaValidationError(f"{field_name} must include timezone information")
    return parsed


def _ensure_exact_keys(
    payload: Mapping[str, Any],
    allowed: set[str],
    context: str,
    required_only: set[str] | None = None,
) -> None:
    if not isinstance(payload, Mapping):
        raise SchemaValidationError(f"{context} must be an object")

    keys = set(payload.keys())
    required = required_only if required_only is not None else allowed

    missing = required - keys
    unknown = keys - allowed

    if missing:
        raise SchemaValidationError(f"{context} missing required field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise SchemaValidationError(f"{context} has unknown field(s): {', '.join(sorted(unknown))}")
