"""Tests for metrics service.

Coverage target: ≥80%
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.metrics_service import (
    MetricsServerError,
    MetricsServerPort,
    MetricsServerStatus,
    MetricsService,
    StartResult,
)


class TestMetricsServerError:
    """Tests for MetricsServerError exception."""

    def test_error_creation(self) -> None:
        """Test MetricsServerError initialization."""
        error = MetricsServerError(port=8000, reason="Port in use")
        assert error.port == 8000
        assert error.reason == "Port in use"
        assert error.original_error is None
        assert "Failed to start metrics server on port 8000" in str(error)
        assert "Port in use" in str(error)

    def test_error_with_original_error(self) -> None:
        """Test MetricsServerError with original exception."""
        original = OSError("Address already in use")
        error = MetricsServerError(
            port=9000, reason="Bind failed", original_error=original
        )
        assert error.original_error is original
        assert error.port == 9000


class TestMetricsServerPort:
    """Tests for MetricsServerPort protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test MetricsServerPort is runtime checkable."""

        class MockServer:
            def start(
                self,
                port: int,
                *,
                fail_fast: bool = False,
                retry_count: int = 3,
                retry_delay: float = 1.0,
            ) -> bool:
                return True

            def is_running(self) -> bool:
                return True

            def reset(self) -> None:
                pass

        assert isinstance(MockServer(), MetricsServerPort)


class TestMetricsServerStatus:
    """Tests for MetricsServerStatus dataclass."""

    def test_status_running(self) -> None:
        """Test MetricsServerStatus for running server."""
        now = datetime.now(tz=UTC)
        status = MetricsServerStatus(running=True, port=8000, started_at=now)
        assert status.running is True
        assert status.port == 8000
        assert status.started_at == now
        assert status.error is None

    def test_status_not_running(self) -> None:
        """Test MetricsServerStatus for stopped server."""
        status = MetricsServerStatus(running=False)
        assert status.running is False
        assert status.port is None
        assert status.started_at is None

    def test_status_with_error(self) -> None:
        """Test MetricsServerStatus with error."""
        status = MetricsServerStatus(running=False, error="Port 8000 in use")
        assert status.error == "Port 8000 in use"


class TestStartResult:
    """Tests for StartResult dataclass."""

    def test_success_result(self) -> None:
        """Test StartResult for successful start."""
        result = StartResult(success=True, port=8000)
        assert result.success is True
        assert result.port == 8000
        assert result.already_running is False
        assert result.error is None

    def test_already_running_result(self) -> None:
        """Test StartResult when server already running."""
        result = StartResult(success=True, port=8000, already_running=True)
        assert result.success is True
        assert result.already_running is True

    def test_failure_result(self) -> None:
        """Test StartResult for failed start."""
        result = StartResult(success=False, port=8000, error="Port in use")
        assert result.success is False
        assert result.error == "Port in use"


class TestMetricsService:
    """Tests for MetricsService."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_server(self) -> MagicMock:
        """Create mock metrics server."""
        server = MagicMock()
        server.is_running.return_value = False
        server.start.return_value = True
        return server

    @pytest.fixture
    def service(self, mock_logger: MagicMock, mock_server: MagicMock) -> MetricsService:
        """Create MetricsService with mocked dependencies."""
        return MetricsService(logger=mock_logger, _server=mock_server)

    def test_start_success(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test successful server start."""
        result = service.start(port=8000)

        assert result.success is True
        assert result.port == 8000
        assert result.already_running is False
        mock_server.start.assert_called_once_with(
            port=8000, fail_fast=False, retry_count=3, retry_delay=1.0
        )

    def test_start_already_running(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test start when server is already running."""
        mock_server.is_running.return_value = True

        result = service.start(port=9000)

        assert result.success is True
        assert result.already_running is True
        mock_server.start.assert_not_called()

    def test_start_failure(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test start when server fails to bind."""
        mock_server.start.return_value = False

        result = service.start(port=8000)

        assert result.success is False
        assert result.error == "Failed to bind port"

    def test_start_with_exception(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test start handles exceptions gracefully."""
        mock_server.start.side_effect = OSError("Address in use")

        result = service.start(port=8000, fail_fast=False)

        assert result.success is False
        assert "Address in use" in (result.error or "")

    def test_start_fail_fast(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test start with fail_fast raises exception."""
        mock_server.start.side_effect = OSError("Address in use")

        with pytest.raises(MetricsServerError) as exc_info:
            service.start(port=8000, fail_fast=True)

        assert exc_info.value.port == 8000
        assert "Address in use" in exc_info.value.reason

    def test_start_custom_params(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test start with custom retry parameters."""
        result = service.start(port=8080, retry_count=5, retry_delay=2.0)

        mock_server.start.assert_called_once_with(
            port=8080, fail_fast=False, retry_count=5, retry_delay=2.0
        )
        assert result.port == 8080

    def test_get_status_running(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test get_status when server is running."""
        # First start the server to set _port and _started_at
        mock_server.is_running.return_value = False
        service.start(port=8000)
        mock_server.is_running.return_value = True

        status = service.get_status()

        assert status.running is True
        assert status.port == 8000
        assert status.started_at is not None

    def test_get_status_not_running(
        self, service: MetricsService, mock_server: MagicMock
    ) -> None:
        """Test get_status when server is not running."""
        mock_server.is_running.return_value = False

        status = service.get_status()

        assert status.running is False
        assert status.port is None
        assert status.started_at is None

    def test_is_running(self, service: MetricsService, mock_server: MagicMock) -> None:
        """Test is_running method."""
        mock_server.is_running.return_value = True
        assert service.is_running() is True

        mock_server.is_running.return_value = False
        assert service.is_running() is False


class TestMetricsServiceEdgeCases:
    """Edge case tests for MetricsService."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    def test_start_logs_correctly(self, mock_logger: MagicMock) -> None:
        """Test that start logs appropriately."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start.return_value = True

        service = MetricsService(logger=mock_logger, _server=mock_server)
        service.start(port=8000)

        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()

    def test_start_already_running_logs_debug(self, mock_logger: MagicMock) -> None:
        """Test that already running logs debug message."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = True

        service = MetricsService(logger=mock_logger, _server=mock_server)
        service.start(port=8000)

        # Debug should be called for "Starting metrics server" and "already running"
        assert mock_logger.debug.call_count >= 2

    def test_handle_start_error_logs_error(self, mock_logger: MagicMock) -> None:
        """Test that _handle_start_error logs error."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False

        service = MetricsService(logger=mock_logger, _server=mock_server)

        exception = RuntimeError("Test error")
        result = service._handle_start_error(port=8000, e=exception, fail_fast=False)

        assert result.success is False
        assert result.error == "Test error"
        mock_logger.error.assert_called_once()

    def test_handle_start_error_fail_fast(self, mock_logger: MagicMock) -> None:
        """Test that _handle_start_error raises when fail_fast=True."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False

        service = MetricsService(logger=mock_logger, _server=mock_server)

        exception = ValueError("Test error")
        with pytest.raises(MetricsServerError) as exc_info:
            service._handle_start_error(port=8000, e=exception, fail_fast=True)

        assert exc_info.value.port == 8000
        assert exc_info.value.original_error is exception

    def test_service_default_port(self, mock_logger: MagicMock) -> None:
        """Test that service uses default port 8000."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start.return_value = True

        service = MetricsService(logger=mock_logger, _server=mock_server)
        result = service.start()

        assert result.port == 8000
        mock_server.start.assert_called_with(
            port=8000, fail_fast=False, retry_count=3, retry_delay=1.0
        )

    def test_start_failure_logs_warning(self, mock_logger: MagicMock) -> None:
        """Test that start failure logs warning."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start.return_value = False

        service = MetricsService(logger=mock_logger, _server=mock_server)
        service.start(port=8000)

        mock_logger.warning.assert_called()

    def test_get_status_uses_stored_port(self, mock_logger: MagicMock) -> None:
        """Test that get_status uses the stored port from start."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = False
        mock_server.start.return_value = True

        service = MetricsService(logger=mock_logger, _server=mock_server)
        service.start(port=9999)

        mock_server.is_running.return_value = True
        status = service.get_status()

        assert status.port == 9999
