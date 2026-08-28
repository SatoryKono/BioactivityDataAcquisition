"""Security regressions for exception-context secret redaction."""

from __future__ import annotations

import json

import pytest

from bioetl.domain.exceptions import NetworkError
from bioetl.domain.exceptions._redaction import _redact_string

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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("password=plain", "password=[REDACTED]"),
        ('token="quoted value"', "token=[REDACTED]"),
        ("secret='quoted value'", "secret=[REDACTED]"),
        ('password="escaped \\" quote"', "password=[REDACTED]"),
        ("token='escaped \\' quote'", "token=[REDACTED]"),
        ('password="alpha\\\nbeta"', "password=[REDACTED]"),
        ('password="unterminated-value', "password=[REDACTED]"),
        ('password="unterminated value', "password=[REDACTED]"),
        ("token='unterminated,value;&tail", "token=[REDACTED]"),
        ('secret="dangling\\', "secret=[REDACTED]"),
        (
            'prefix password="one two", token=three; safe',
            "prefix password=[REDACTED], token=[REDACTED]; safe",
        ),
        ("password=secret\u00a0safe", "password=[REDACTED]\u00a0safe"),
        ("password=secret\fsafe", "password=[REDACTED]\fsafe"),
        ("tokenization=value", "tokenization=value"),
    ],
)
def test_inline_secret_redaction_preserves_supported_quoted_grammar(
    value: str,
    expected: str,
) -> None:
    """Quoted, escaped, and safe-negative forms retain their contract."""
    assert _redact_string(value) == expected


@pytest.mark.timeout(2)
@pytest.mark.parametrize(("quote", "pair"), [('"', r"\!"), ("'", r"\&")])
def test_inline_secret_redaction_rejects_redos_payload_in_bounded_time(
    quote: str,
    pair: str,
) -> None:
    """Ambiguous escaped characters must not trigger exponential backtracking."""
    redacted = _redact_string(f"password={quote}{pair * 50_000}")

    assert redacted == "password=[REDACTED]"


def test_malformed_quoted_secret_is_fail_closed_through_exception_context() -> None:
    """Malformed quoted values must not leak through the public exception payload."""
    secret = "unterminated value,with;&delimiters"
    error = NetworkError(f'password="{secret}')

    serialized = json.dumps(error.to_structured_context())

    assert secret not in serialized
    assert "password=[REDACTED]" in serialized
