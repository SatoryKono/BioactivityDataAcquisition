"""Tests for infrastructure/observability/metrics_server_adapter.py.

Verifies the MetricsServerAdapter implementation.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.ports import MetricsServerRuntimeStatus
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)


@pytest.mark.unit
class TestMetricsServerAdapter:
    """Tests for MetricsServerAdapter class."""

    @pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
    def reset_server_state(self) -> Generator[None, None, None]:
        """Reset server state before each test."""
        from bioetl.infrastructure.observability.server import reset_server_state

        reset_server_state()
        yield
        reset_server_state()

    def test_init_without_logger(self) -> None:
        """Test adapter can be initialized without logger."""
        adapter = MetricsServerAdapter()

        assert adapter._logger is None

    def test_init_with_logger(self) -> None:
        """Test adapter can be initialized with logger."""
        mock_logger = MagicMock()
        adapter = MetricsServerAdapter(logger=mock_logger)

        assert adapter._logger is mock_logger

    def test_start_calls_start_metrics_server(self) -> None:
        """Test start method delegates to start_metrics_server."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            result = adapter.start(port=9000)

            assert result is True
            mock_start.assert_called_once_with(
                port=9000,
                addr="0.0.0.0",
                fail_fast=False,
                retry_count=3,
                retry_delay=1.0,
                logger=None,
            )

    def test_start_with_all_parameters(self) -> None:
        """Test start method passes all parameters correctly."""
        mock_logger = MagicMock()
        adapter = MetricsServerAdapter(logger=mock_logger)

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            result = adapter.start(
                port=8080,
                fail_fast=True,
                retry_count=5,
                retry_delay=2.0,
            )

            assert result is True
            mock_start.assert_called_once_with(
                port=8080,
                addr="0.0.0.0",
                fail_fast=True,
                retry_count=5,
                retry_delay=2.0,
                logger=mock_logger,
            )

    def test_start_returns_false_on_failure(self) -> None:
        """Test start returns False when server fails to start."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = False
            result = adapter.start()

            assert result is False

    def test_is_running_initial_state(self) -> None:
        """Test is_running returns False initially."""
        adapter = MetricsServerAdapter()

        assert adapter.is_running() is False

    def test_is_running_after_start(self) -> None:
        """Test is_running returns True after server starts."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.is_metrics_server_running"
        ) as mock_is_running:
            mock_is_running.return_value = True
            assert adapter.is_running() is True
            mock_is_running.assert_called_once_with()

    def test_get_runtime_status_delegates_to_server_module(self) -> None:
        """Test runtime status metadata is delegated to the server module."""
        adapter = MetricsServerAdapter()
        runtime_status = MetricsServerRuntimeStatus(running=True, port=8000)

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.get_metrics_server_runtime_status"
        ) as mock_get_status:
            mock_get_status.return_value = runtime_status
            result = adapter.get_runtime_status()

        assert result == runtime_status
        mock_get_status.assert_called_once_with()

    def test_is_running_reads_live_server_state(self) -> None:
        """Test is_running reads the current state from the server module."""
        from bioetl.infrastructure.observability import server as obs_server

        adapter = MetricsServerAdapter()
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            obs_server.start_metrics_server(port=9999)

        assert adapter.is_running() is True

    def test_get_runtime_status_reads_live_server_state(self) -> None:
        """Test runtime status reads the current snapshot from the server module."""
        from bioetl.infrastructure.observability import server as obs_server

        adapter = MetricsServerAdapter()
        with patch("bioetl.infrastructure.observability.server.start_http_server"):
            obs_server.start_metrics_server(port=9999, addr="127.0.0.1")

        status = adapter.get_runtime_status()
        assert status.running is True
        assert status.port == 9999
        assert status.addr == "127.0.0.1"
        assert status.started_at is not None

    def test_reset_calls_reset_server_state(self) -> None:
        """Test reset method calls reset_server_state."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.reset_server_state"
        ) as mock_reset:
            adapter.reset()
            mock_reset.assert_called_once()

    def test_reset_allows_restart(self) -> None:
        """Test reset allows server to be started again."""
        adapter = MetricsServerAdapter()

        # First start
        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()

        # Reset
        adapter.reset()

        # Should be able to start again
        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()
            # The mock should be called (actual behavior depends on implementation)
            mock_start.assert_called()


@pytest.mark.unit
class TestMetricsServerAdapterDefaults:
    """Tests for default parameter values."""

    def test_default_port(self) -> None:
        """Test default port is 8000."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()

            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["port"] == 8000

    def test_default_fail_fast(self) -> None:
        """Test default fail_fast is False."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()

            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["fail_fast"] is False

    def test_default_retry_count(self) -> None:
        """Test default retry_count is 3."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()

            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["retry_count"] == 3

    def test_default_retry_delay(self) -> None:
        """Test default retry_delay is 1.0."""
        adapter = MetricsServerAdapter()

        with patch(
            "bioetl.infrastructure.observability.metrics_server_adapter.start_metrics_server"
        ) as mock_start:
            mock_start.return_value = True
            adapter.start()

            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["retry_delay"] == pytest.approx(1.0)
