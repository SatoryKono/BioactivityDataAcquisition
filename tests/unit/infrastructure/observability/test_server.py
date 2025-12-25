"""Unit tests for Prometheus metrics server."""

from __future__ import annotations

import errno
from unittest.mock import patch

import pytest

from bioetl.infrastructure.observability.server import (
    MetricsServerError,
    reset_server_state,
    start_metrics_server,
)


@pytest.fixture(autouse=True)
def reset_server():
    """Reset server state before each test."""
    reset_server_state()
    yield
    reset_server_state()


@pytest.mark.unit
class TestStartMetricsServer:
    """Tests for start_metrics_server function."""

    def test_returns_true_on_success(self):
        """Test successful server start returns True."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            result = start_metrics_server(port=9999)

            assert result is True
            mock_server.assert_called_once_with(9999)

    def test_idempotent_multiple_calls(self):
        """Test server is only started once."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            result1 = start_metrics_server(port=9999)
            result2 = start_metrics_server(port=9999)

            assert result1 is True
            assert result2 is True
            # Should only be called once
            mock_server.assert_called_once()

    def test_lenient_mode_returns_false_on_port_conflict(self):
        """Test fail_fast=False returns False on port conflict instead of raising."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(port=8000, fail_fast=False)

            assert result is False

    def test_fail_fast_raises_on_port_conflict(self):
        """Test fail_fast=True raises MetricsServerError on port conflict."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(port=8000, fail_fast=True)

            assert exc_info.value.port == 8000
            assert exc_info.value.reason == "port_in_use"
            assert exc_info.value.original_error is error

    def test_fail_fast_raises_on_other_os_error(self):
        """Test fail_fast=True raises on other OS errors."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EACCES  # Permission denied
            mock_server.side_effect = error

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(port=80, fail_fast=True, retry_count=1)

            assert exc_info.value.reason == "os_error"

    def test_fail_fast_raises_on_unexpected_error(self):
        """Test fail_fast=True raises on unexpected exceptions."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            mock_server.side_effect = RuntimeError("Unexpected")

            with pytest.raises(MetricsServerError) as exc_info:
                start_metrics_server(port=8000, fail_fast=True)

            assert exc_info.value.reason == "unexpected"

    def test_lenient_mode_returns_false_on_unexpected_error(self):
        """Test fail_fast=False returns False on unexpected error."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            mock_server.side_effect = RuntimeError("Unexpected")

            result = start_metrics_server(port=8000, fail_fast=False)

            assert result is False

    def test_retry_on_transient_os_error(self):
        """Test retries on transient OS errors (not EADDRINUSE)."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.ECONNREFUSED
            # Fail twice, succeed on third attempt
            mock_server.side_effect = [error, error, None]

            with patch("bioetl.infrastructure.observability.server.time.sleep"):
                result = start_metrics_server(
                    port=8000, fail_fast=False, retry_count=3, retry_delay=0.01
                )

            assert result is True
            assert mock_server.call_count == 3

    def test_no_retry_on_port_conflict(self):
        """Test no retries when port is in use (EADDRINUSE)."""
        with patch(
            "bioetl.infrastructure.observability.server.start_http_server"
        ) as mock_server:
            error = OSError()
            error.errno = errno.EADDRINUSE
            mock_server.side_effect = error

            result = start_metrics_server(
                port=8000, fail_fast=False, retry_count=3
            )

            assert result is False
            # Should only try once for EADDRINUSE
            mock_server.assert_called_once()


@pytest.mark.unit
class TestMetricsServerError:
    """Tests for MetricsServerError exception."""

    def test_error_attributes(self):
        """Test MetricsServerError has correct attributes."""
        original = OSError("original")
        error = MetricsServerError(port=8000, reason="test", original_error=original)

        assert error.port == 8000
        assert error.reason == "test"
        assert error.original_error is original
        assert "8000" in str(error)
        assert "test" in str(error)

    def test_error_without_original(self):
        """Test MetricsServerError works without original_error."""
        error = MetricsServerError(port=9000, reason="timeout")

        assert error.port == 9000
        assert error.reason == "timeout"
        assert error.original_error is None
