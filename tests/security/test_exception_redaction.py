"""Security regressions for exception-context secret redaction."""

from __future__ import annotations

import json

import pytest

from bioetl.domain.exceptions import NetworkError

pytestmark = [pytest.mark.security, pytest.mark.unit]


def test_structured_exception_context_redacts_hostile_nested_secrets() -> None:
    """Secrets must not escape through nested values or wrapped exceptions."""
    raw_secrets = (
        "bearer-secret",
        "sk_live_123456",
        "url-password",
        "query-secret",
        "nested-password",
    )
    error = NetworkError("Bearer bearer-secret sk_live_123456").with_context(
        nested={
            "items": [
                "https://user:url-password@example.org/path?query=query-secret",
                ValueError("password=nested-password"),
            ],
            "private-key": "private-key-secret",
            "unordered": {"Bearer set-secret", "safe-value"},
        }
    )

    payload = error.to_structured_context()
    serialized = json.dumps(payload)

    assert "[REDACTED]" in serialized
    for secret in raw_secrets:
        assert secret not in serialized
    assert "private-key-secret" not in serialized
    assert "set-secret" not in serialized


def test_structured_exception_context_preserves_safe_url_shape() -> None:
    """Redaction keeps useful endpoint context without credentials or values."""
    error = NetworkError("request failed").with_context(
        endpoint="prefix https://user:pw@example.org:8443/path?cursor=secret suffix"
    )

    endpoint = error.to_structured_context()["endpoint"]

    assert endpoint == ("prefix https://example.org:8443/path?[REDACTED] suffix")
