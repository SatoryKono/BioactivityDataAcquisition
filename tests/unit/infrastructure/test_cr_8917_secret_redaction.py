# pyright: reportArgumentType=false
"""Focused secret-redaction regressions for #8917."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.adapters.decorators._retry_support import (
    _redact_transport_error_message,
)
from bioetl.infrastructure.observability.logging_config import _SECRET_PATTERNS
from scripts.engineering.qa.vcr.check_vcr_secrets import _looks_redacted
from scripts.ops.maintenance.security.salt_rotate import (
    ENV_ROTATION_ACTIVE,
    ENV_SALT_NEXT,
    MIN_SALT_LENGTH,
    complete_rotation,
)

pytestmark = pytest.mark.unit


def test_redact_transport_error_keeps_bearer_token_out_of_message() -> None:
    leaked = "Authorization: Bearer super-secret-token-value"
    redacted = _redact_transport_error_message(leaked)
    assert "super-secret-token-value" not in redacted
    assert "<redacted>" in redacted.lower() or "REDACTED" in redacted


def test_logging_config_authorization_regex_consumes_token() -> None:
    raw = "Authorization: Bearer super-secret-token-value"
    redacted = raw
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    assert "super-secret-token-value" not in redacted


def test_vcr_secret_checker_does_not_treat_substring_as_redacted() -> None:
    assert _looks_redacted("[REDACTED]") is True
    assert _looks_redacted("redacted") is True
    assert _looks_redacted("my-test-token") is False
    assert _looks_redacted("example_live_key") is False
    assert _looks_redacted("unredacted_secret") is False


def test_complete_rotation_rejects_short_next_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_ROTATION_ACTIVE, "true")
    monkeypatch.setenv(ENV_SALT_NEXT, "too-short")
    result = complete_rotation()
    assert result.success is False
    assert result.error is not None
    assert str(MIN_SALT_LENGTH) in result.error


def test_wsl_startup_does_not_pass_password_on_python_argv() -> None:
    script = Path("scripts/memory/setup/wsl_startup.sh").read_text(encoding="utf-8")
    assert 'python3 - "$file_path" "$key" "$value"' not in script
    assert "BIOETL_ENV_UPSERT_VALUE" in script
    assert 'os.environ["BIOETL_ENV_UPSERT_VALUE"]' in script
