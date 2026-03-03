# Module Development Guide

All analyzers MUST return a `ModuleResult` payload from `backend.schemas.module_result`.

## Required output contract

Every module output must include these required fields:

- `module`
- `status`
- `score`
- `findings`
- `started_at`
- `completed_at`
- `trace_id`
- `schema_version`

`status` values are strictly limited to:

- `queued`
- `running`
- `completed`
- `failed`
- `partial`

Each entry in `findings` must be an object with:

- `severity`
- `category`
- `evidence`
- `recommendation`

## Backward compatibility policy

The schema uses semantic versioning via `schema_version`.

- Consumers accept payloads where the **major** version matches their expected version.
- Minor and patch versions may add compatible fields/behavior while preserving existing required fields.
- Any major version bump is treated as breaking and requires coordinated producer/consumer rollout.

Use `is_schema_compatible()` from `backend.schemas.module_result` to enforce this policy.

## Boundary validation (required)

Before any module result is published to a queue/event bus or streamed to clients, validate it:

```python
from backend.schemas.module_result import validate_before_publish

safe_payload = validate_before_publish(raw_payload)
publish(safe_payload)
```

Do **not** bypass this validation in analyzer implementations.

## Error envelope for failed modules

When `status == "failed"`, include the `error` envelope with this shape:

- `code` (string)
- `message` (string)
- `details` (object)
- `retryable` (boolean)

For all non-failed statuses, `error` must be omitted.
