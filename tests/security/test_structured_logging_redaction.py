"""Security regressions for structured logging secret filters.REQ-GOV-010: structured logs redact secrets."""

from __future__ import annotations

import json

import pytest

from bioetl.infrastructure.observability.logging_config import secret_filter_processor

pytestmark = [pytest.mark.security, pytest.mark.unit]


def test_log_processor_recursively_redacts_keys_bearer_and_prefixed_tokens() -> None:
    secrets = ("bearer-secret", "password-secret", "sk_live_123456")
    event = {
        "authorization": "Bearer bearer-secret",
        "nested": {
            "password": "password-secret",
            "items": ["safe", "sk_live_123456"],
        },
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
    }

    filtered = secret_filter_processor(None, "info", event)
    serialized = json.dumps(filtered)

    for secret in secrets:
        assert secret not in serialized
    assert filtered["run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert "[REDACTED" in serialized
