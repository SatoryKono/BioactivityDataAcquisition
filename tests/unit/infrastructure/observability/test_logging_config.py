"""Unit tests for logging_config.py.

Tests the centralized structlog configuration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestConfigureLogging:
    """Tests for configure_logging function."""

    @pytest.fixture(autouse=True)
    def reset_config(self) -> None:
        """Reset logging configuration before each test."""
        from bioetl.infrastructure.observability.logging_config import (
            reset_logging_config,
        )

        reset_logging_config()
        yield
        reset_logging_config()

    def test_configure_json_format(self) -> None:
        """Test configuring with JSON format."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        result = configure_logging(json_format=True, log_level="INFO")
        assert result is True

    def test_configure_console_format(self) -> None:
        """Test configuring with console format."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        result = configure_logging(json_format=False, log_level="DEBUG")
        assert result is True

    def test_configure_already_configured_returns_false(self) -> None:
        """Test that subsequent calls without force return False."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        result1 = configure_logging(json_format=True)
        result2 = configure_logging(json_format=True)

        assert result1 is True
        assert result2 is False

    def test_configure_with_force_reconfigures(self) -> None:
        """Test that force=True reconfigures logging."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        result1 = configure_logging(json_format=True)
        result2 = configure_logging(json_format=False, force=True)

        assert result1 is True
        assert result2 is True

    def test_configure_format_mismatch_no_reconfigure(self) -> None:
        """Test that format mismatch doesn't reconfigure without force."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        # First configure with JSON
        result1 = configure_logging(json_format=True)
        # Try to configure with console (format mismatch)
        result2 = configure_logging(json_format=False)

        assert result1 is True
        # Should return False without reconfiguring
        assert result2 is False

    def test_configure_different_log_levels(self) -> None:
        """Test configuring with different log levels."""
        from bioetl.infrastructure.observability.logging_config import (
            configure_logging,
            reset_logging_config,
        )

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            reset_logging_config()
            result = configure_logging(log_level=level)
            assert result is True

    def test_configure_writes_logs_to_file_when_env_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that BIOETL_LOG_FILE adds a file sink alongside stdout."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        log_path = tmp_path / "runtime" / "bioetl.log"
        monkeypatch.setenv("BIOETL_LOG_FILE", str(log_path))

        result = configure_logging(json_format=False, force=True)

        assert result is True
        logging.getLogger("bioetl.test").info("file sink smoke")

        assert log_path.exists()
        assert "file sink smoke" in log_path.read_text(encoding="utf-8")

    def test_configure_uses_default_runtime_log_file_outside_pytest(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Test that normal runtime defaults to logs/bioetl.log."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        monkeypatch.delenv("BIOETL_LOG_FILE", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.chdir(tmp_path)

        result = configure_logging(json_format=False, force=True)

        assert result is True
        logging.getLogger("bioetl.test").info("default file sink smoke")

        log_path = tmp_path / "logs" / "bioetl.log"
        assert log_path.exists()
        assert "default file sink smoke" in log_path.read_text(encoding="utf-8")

    def test_configure_formats_foreign_stdlib_logs_as_json(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that foreign stdlib loggers are rendered as structured JSON."""
        from bioetl.infrastructure.observability.logging_config import configure_logging

        result = configure_logging(json_format=True, log_level="INFO", force=True)

        assert result is True
        logging.getLogger("httpx").info(
            'HTTP Request: GET https://example.test "HTTP/1.1 200 OK"'
        )

        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())

        assert payload["event"].startswith("HTTP Request: GET https://example.test")
        assert payload["logger"] == "httpx"
        assert payload["level"] == "info"
        assert "timestamp" in payload


@pytest.mark.unit
class TestIsLoggingConfigured:
    """Tests for is_logging_configured function."""

    @pytest.fixture(autouse=True)
    def reset_config(self) -> None:
        """Reset logging configuration before each test."""
        from bioetl.infrastructure.observability.logging_config import (
            reset_logging_config,
        )

        reset_logging_config()
        yield
        reset_logging_config()

    def test_returns_false_initially(self) -> None:
        """Test that is_logging_configured returns False initially."""
        from bioetl.infrastructure.observability.logging_config import (
            is_logging_configured,
        )

        assert is_logging_configured() is False

    def test_returns_true_after_configure(self) -> None:
        """Test that is_logging_configured returns True after configure."""
        from bioetl.infrastructure.observability.logging_config import (
            configure_logging,
            is_logging_configured,
        )

        configure_logging()
        assert is_logging_configured() is True


@pytest.mark.unit
class TestResetLoggingConfig:
    """Tests for reset_logging_config function."""

    def test_reset_clears_configuration(self) -> None:
        """Test that reset clears the configuration state."""
        from bioetl.infrastructure.observability.logging_config import (
            configure_logging,
            is_logging_configured,
            reset_logging_config,
        )

        configure_logging()
        assert is_logging_configured() is True

        reset_logging_config()
        assert is_logging_configured() is False

    def test_reset_allows_reconfigure(self) -> None:
        """Test that reset allows reconfiguration."""
        from bioetl.infrastructure.observability.logging_config import (
            configure_logging,
            reset_logging_config,
        )

        result1 = configure_logging(json_format=True)
        reset_logging_config()
        result2 = configure_logging(json_format=False)

        assert result1 is True
        assert result2 is True


@pytest.mark.unit
class TestSecretFilterProcessor:
    """Tests for secret_filter_processor function."""

    def test_masks_api_key(self) -> None:
        """Test that API keys are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"message": "api_key=abc123xyz"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "abc123xyz" not in result["message"]
        assert "[REDACTED" in result["message"]

    def test_masks_authorization_header(self) -> None:
        """Test that authorization headers are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        # Test auth=value pattern
        event_dict = {"message": "auth=secrettoken123"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "secrettoken123" not in result["message"]
        assert "REDACTED" in result["message"]

    def test_masks_password(self) -> None:
        """Test that passwords are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"message": "password=secretpass123"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "secretpass123" not in result["message"]
        assert "[REDACTED" in result["message"]

    def test_masks_token(self) -> None:
        """Test that tokens are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"message": "token=mytoken123"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "mytoken123" not in result["message"]
        assert "[REDACTED" in result["message"]

    def test_masks_aws_key(self) -> None:
        """Test that AWS-style keys are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"message": "key: AKIAIOSFODNN7EXAMPLE"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "AKIAIOSFODNN7EXAMPLE" not in result["message"]
        assert "[REDACTED" in result["message"]

    def test_preserves_non_secret_values(self) -> None:
        """Test that non-secret values are preserved."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"message": "Processing record 123", "count": 42}
        result = secret_filter_processor(None, "info", event_dict)

        assert result["message"] == "Processing record 123"
        assert result["count"] == 42

    def test_handles_non_string_values(self) -> None:
        """Test that non-string values are not modified."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"count": 100, "ratio": 0.5, "enabled": True}
        result = secret_filter_processor(None, "info", event_dict)

        assert result["count"] == 100
        assert result["ratio"] == pytest.approx(0.5)
        assert result["enabled"] is True

    def test_handles_nested_dict(self) -> None:
        """Test that nested dicts are processed."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        # The pattern matcher looks for patterns like "api_key=value" within strings
        event_dict = {
            "config": {
                "connection_string": "api_key=secret123&host=localhost",
                "host": "localhost",
            }
        }
        result = secret_filter_processor(None, "info", event_dict)

        # The nested string containing "api_key=value" pattern should be masked
        assert "secret123" not in result["config"]["connection_string"]
        assert "[REDACTED" in result["config"]["connection_string"]
        # Non-secret values are preserved
        assert result["config"]["host"] == "localhost"

    def test_masks_bearer_token(self) -> None:
        """Test that Bearer tokens are masked."""
        from bioetl.infrastructure.observability.logging_config import (
            secret_filter_processor,
        )

        event_dict = {"header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        result = secret_filter_processor(None, "info", event_dict)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result["header"]
        assert "Bearer [REDACTED]" in result["header"]


@pytest.mark.unit
class TestTraceContextProcessor:
    """Tests for trace_context_processor function."""

    def test_noop_without_trace_identifiers(self) -> None:
        """Processor should leave event unchanged when no trace context exists."""
        from bioetl.infrastructure.observability.logging_config import (
            trace_context_processor,
        )

        event_dict = {"event": "pipeline-started", "pipeline": "chembl_activity"}
        with patch(
            "bioetl.infrastructure.observability.logging_config._get_current_trace_identifiers",
            return_value=None,
        ):
            result = trace_context_processor(None, "info", event_dict.copy())

        assert result == event_dict
        assert "trace_id" not in result
        assert "span_id" not in result

    def test_injects_trace_and_span_ids_when_available(self) -> None:
        """Processor should inject trace identifiers when helper returns them."""
        from bioetl.infrastructure.observability.logging_config import (
            trace_context_processor,
        )

        with patch(
            "bioetl.infrastructure.observability.logging_config._get_current_trace_identifiers",
            return_value=(
                "0123456789abcdef0123456789abcdef",
                "0123456789abcdef",
            ),
        ):
            result = trace_context_processor(
                None,
                "info",
                {"event": "pipeline-started", "pipeline": "chembl_activity"},
            )

        assert result["trace_id"] == "0123456789abcdef0123456789abcdef"
        assert result["span_id"] == "0123456789abcdef"

    def test_keeps_existing_trace_fields(self) -> None:
        """Processor should not overwrite explicitly bound trace identifiers."""
        from bioetl.infrastructure.observability.logging_config import (
            trace_context_processor,
        )

        with patch(
            "bioetl.infrastructure.observability.logging_config._get_current_trace_identifiers",
            return_value=("00000000000000000000000000000001", "0000000000000002"),
        ):
            result = trace_context_processor(
                None,
                "info",
                {
                    "event": "pipeline-started",
                    "trace_id": "bound-trace",
                    "span_id": "bound-span",
                },
            )

        assert result["trace_id"] == "bound-trace"
        assert result["span_id"] == "bound-span"


@pytest.mark.unit
class TestMaskSecrets:
    """Tests for _mask_secrets helper function."""

    def test_non_string_returns_unchanged(self) -> None:
        """Test that non-string values are returned unchanged."""
        from bioetl.infrastructure.observability.logging_config import _mask_secrets

        assert _mask_secrets(123) == 123
        assert _mask_secrets(45.67) == pytest.approx(45.67)
        assert _mask_secrets(True) is True
        assert _mask_secrets(None) is None
        assert _mask_secrets([1, 2, 3]) == [1, 2, 3]

    def test_empty_string_unchanged(self) -> None:
        """Test that empty string is unchanged."""
        from bioetl.infrastructure.observability.logging_config import _mask_secrets

        assert _mask_secrets("") == ""

    def test_safe_string_unchanged(self) -> None:
        """Test that safe strings are unchanged."""
        from bioetl.infrastructure.observability.logging_config import _mask_secrets

        assert _mask_secrets("Hello World") == "Hello World"
        assert _mask_secrets("count=42") == "count=42"


@pytest.mark.unit
class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports(self) -> None:
        """Test that __all__ contains expected items."""
        from bioetl.infrastructure.observability import logging_config

        expected = [
            "configure_logging",
            "is_logging_configured",
            "reset_logging_config",
            "secret_filter_processor",
            "trace_context_processor",
        ]
        for name in expected:
            assert name in logging_config.__all__

    def test_exports_are_callable(self) -> None:
        """Test that all exports are actually available."""
        from bioetl.infrastructure.observability.logging_config import (
            configure_logging,
            is_logging_configured,
            reset_logging_config,
            secret_filter_processor,
            trace_context_processor,
        )

        assert callable(configure_logging)
        assert callable(is_logging_configured)
        assert callable(reset_logging_config)
        assert callable(secret_filter_processor)
        assert callable(trace_context_processor)
