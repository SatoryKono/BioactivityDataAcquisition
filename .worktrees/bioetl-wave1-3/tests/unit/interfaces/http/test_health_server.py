"""Tests for HTTP health server."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.types import HealthResponse


class TestHealthResponse:
    """Tests for HealthResponse dataclass."""

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        response = HealthResponse(
            status="healthy",
            timestamp="2024-01-01T00:00:00Z",
            checks={"server": {"status": "healthy"}},
        )
        json_str = response.to_json()
        data = json.loads(json_str)

        assert data["status"] == "healthy"
        assert data["timestamp"] == "2024-01-01T00:00:00Z"
        assert data["version"] == "1.0.0"
        assert data["checks"]["server"]["status"] == "healthy"

    def test_http_status_healthy(self) -> None:
        """Test HTTP status code for healthy status."""
        response = HealthResponse(
            status="healthy",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert response.http_status == 200

    def test_http_status_degraded(self) -> None:
        """Test HTTP status code for degraded status."""
        response = HealthResponse(
            status="degraded",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert response.http_status == 200  # Degraded is still operational

    def test_http_status_unhealthy(self) -> None:
        """Test HTTP status code for unhealthy status."""
        response = HealthResponse(
            status="unhealthy",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert response.http_status == 503


class TestHealthServer:
    """Tests for HealthServer class."""

    @pytest.fixture
    def mock_health_monitor(self) -> MagicMock:
        """Create a mock health monitor."""
        monitor = MagicMock()
        monitor.get_all_states.return_value = {}
        return monitor

    @pytest.mark.asyncio
    async def test_server_start_stop(self) -> None:
        """Test server start and stop lifecycle."""
        server = HealthServer(host="127.0.0.1", port=0)  # Port 0 = random available

        await server.start()
        assert server.is_running
        assert server.uptime_seconds >= 0

        await server.stop()
        assert not server.is_running

    @pytest.mark.asyncio
    async def test_server_uptime(self) -> None:
        """Test uptime tracking."""
        server = HealthServer(host="127.0.0.1", port=0)

        assert server.uptime_seconds == 0.0

        await server.start()
        await asyncio.sleep(0.1)
        assert server.uptime_seconds > 0

        await server.stop()

    @pytest.mark.asyncio
    async def test_handle_health_without_monitor(self) -> None:
        """Test /health endpoint without health monitor."""
        server = HealthServer(host="127.0.0.1", port=0)

        await server.start()
        try:
            response = await server._handle_health()

            assert response.status == "healthy"
            assert "server" in response.checks
            assert response.checks["server"]["status"] == "healthy"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_health_with_monitor(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test /health endpoint with health monitor."""
        # Setup mock to return provider states
        mock_state = MagicMock()
        mock_state.status = HealthStatus.HEALTHY
        mock_state.consecutive_errors = 0
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        await server.start()
        try:
            response = await server._handle_health()

            assert response.status == "healthy"
            assert "providers" in response.checks
            assert "chembl" in response.checks["providers"]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_liveness(self) -> None:
        """Test /health/live endpoint always returns healthy."""
        server = HealthServer(host="127.0.0.1", port=0)

        await server.start()
        try:
            response = await server._handle_liveness()

            assert response.status == "healthy"
            assert response.http_status == 200
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_readiness_healthy(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test /health/ready endpoint with healthy providers."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.HEALTHY
        mock_state.consecutive_errors = 0
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        await server.start()
        try:
            response = await server._handle_readiness()

            assert response.status == "healthy"
            assert response.http_status == 200
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_readiness_unhealthy(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test /health/ready endpoint with unhealthy providers."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.UNHEALTHY
        mock_state.consecutive_errors = 5
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        await server.start()
        try:
            response = await server._handle_readiness()

            assert response.status == "unhealthy"
            assert response.http_status == 503
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_providers(self, mock_health_monitor: MagicMock) -> None:
        """Test /health/providers endpoint."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.DEGRADED
        mock_state.consecutive_errors = 2
        mock_health_monitor.get_all_states.return_value = {
            "chembl": mock_state,
            "pubchem": mock_state,
        }

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        await server.start()
        try:
            response = await server._handle_providers()

            assert "providers" in response.checks
            assert "chembl" in response.checks["providers"]
            assert "pubchem" in response.checks["providers"]
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_overall_status_aggregation(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test that overall status is worst of all providers."""
        healthy_state = MagicMock()
        healthy_state.status = HealthStatus.HEALTHY

        unhealthy_state = MagicMock()
        unhealthy_state.status = HealthStatus.UNHEALTHY

        mock_health_monitor.get_all_states.return_value = {
            "chembl": healthy_state,
            "pubchem": unhealthy_state,
        }

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        status = server._get_overall_status()
        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_overall_status_degraded(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test that overall status is degraded when worst is degraded."""
        healthy_state = MagicMock()
        healthy_state.status = HealthStatus.HEALTHY

        degraded_state = MagicMock()
        degraded_state.status = HealthStatus.DEGRADED

        mock_health_monitor.get_all_states.return_value = {
            "chembl": healthy_state,
            "pubchem": degraded_state,
        }

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            health_monitor=mock_health_monitor,
        )

        status = server._get_overall_status()
        assert status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_handle_readiness_without_monitor(self) -> None:
        """Test /health/ready endpoint without health monitor."""
        server = HealthServer(host="127.0.0.1", port=0)

        await server.start()
        try:
            response = await server._handle_readiness()

            assert response.status == "healthy"
            assert response.checks.get("message") == "No health monitor configured"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_handle_providers_without_monitor(self) -> None:
        """Test /health/providers endpoint without health monitor."""
        server = HealthServer(host="127.0.0.1", port=0)

        await server.start()
        try:
            response = await server._handle_providers()

            assert response.status == "healthy"
            assert response.checks.get("message") == "No health monitor configured"
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_with_logger(self) -> None:
        """Test server lifecycle with logger."""
        mock_logger = MagicMock()
        server = HealthServer(host="127.0.0.1", port=0, logger=mock_logger)

        await server.start()
        mock_logger.info.assert_called_with(
            "health_server_started", host="127.0.0.1", port=0
        )

        await server.stop()
        mock_logger.info.assert_called_with("health_server_stopped")

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self) -> None:
        """Test stopping a server that was never started."""
        server = HealthServer(host="127.0.0.1", port=0)
        # Should not raise
        await server.stop()
        assert not server.is_running

    @pytest.mark.asyncio
    async def test_is_running_false_initially(self) -> None:
        """Test is_running property before start."""
        server = HealthServer(host="127.0.0.1", port=0)
        assert not server.is_running


class TestHealthServerHTTP:
    """Tests for HTTP request handling via actual connections."""

    @pytest.fixture
    async def running_server(self) -> HealthServer:
        """Create and start a health server."""
        server = HealthServer(host="127.0.0.1", port=0)
        await server.start()
        yield server
        await server.stop()

    def _get_server_port(self, server: HealthServer) -> int:
        """Get the actual port of the running server."""
        # Access the internal server to get the assigned port
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(
        self, port: int, method: str = "GET", path: str = "/health"
    ) -> tuple[int, str, str]:
        """Send HTTP request and return status code, status text, and body."""
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()

            # Read response
            response_line = await reader.readline()
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])
            status_text = parts[2] if len(parts) > 2 else ""

            # Read headers
            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                header_line = line.decode("utf-8").strip()
                if ":" in header_line:
                    key, value = header_line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # Read body
            content_length = int(headers.get("content-length", 0))
            body = await reader.read(content_length)
            return status_code, status_text, body.decode("utf-8")
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_http_health_endpoint(self, running_server: HealthServer) -> None:
        """Test /health endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "server" in data["checks"]

    @pytest.mark.asyncio
    async def test_http_healthz_endpoint(self, running_server: HealthServer) -> None:
        """Test /healthz endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/healthz")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_http_liveness_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/live endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health/live")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "server" in data["checks"]

    @pytest.mark.asyncio
    async def test_http_readiness_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/ready endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health/ready")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_http_providers_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/providers endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(
            port, "GET", "/health/providers"
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_http_404_not_found(self, running_server: HealthServer) -> None:
        """Test 404 response for unknown path."""
        port = self._get_server_port(running_server)
        status_code, status_text, body = await self._send_request(
            port, "GET", "/unknown"
        )

        assert status_code == 404
        assert status_text == "Not Found"
        data = json.loads(body)
        assert data["error"] == "Not Found"

    @pytest.mark.asyncio
    async def test_http_405_method_not_allowed(
        self, running_server: HealthServer
    ) -> None:
        """Test 405 response for non-GET methods."""
        port = self._get_server_port(running_server)
        status_code, status_text, body = await self._send_request(
            port, "POST", "/health"
        )

        assert status_code == 405
        assert status_text == "Method Not Allowed"
        data = json.loads(body)
        assert data["error"] == "Method Not Allowed"

    @pytest.mark.asyncio
    async def test_http_bad_request(self, running_server: HealthServer) -> None:
        """Test 400 response for malformed request."""
        port = self._get_server_port(running_server)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            # Send malformed request (no path)
            writer.write(b"INVALID\r\n\r\n")
            await writer.drain()

            response_line = await reader.readline()
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])

            assert status_code == 400
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_http_query_string_stripped(
        self, running_server: HealthServer
    ) -> None:
        """Test that query strings are stripped from path."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health?foo=bar")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_http_empty_request(self, running_server: HealthServer) -> None:
        """Test handling of empty request."""
        port = self._get_server_port(running_server)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            # Send empty request and close
            writer.write_eof()
            await writer.drain()
            # Should not raise, server handles gracefully
        finally:
            writer.close()
            await writer.wait_closed()


class TestHealthServerWithMonitor:
    """Tests for health server with health monitor configured."""

    @pytest.fixture
    def mock_health_monitor(self) -> MagicMock:
        """Create a mock health monitor."""
        monitor = MagicMock()
        monitor.get_all_states.return_value = {}
        return monitor

    @pytest.fixture
    async def running_server_with_monitor(
        self, mock_health_monitor: MagicMock
    ) -> HealthServer:
        """Create and start a health server with monitor."""
        server = HealthServer(
            host="127.0.0.1", port=0, health_monitor=mock_health_monitor
        )
        await server.start()
        yield server
        await server.stop()

    def _get_server_port(self, server: HealthServer) -> int:
        """Get the actual port of the running server."""
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(
        self, port: int, method: str = "GET", path: str = "/health"
    ) -> tuple[int, str, str]:
        """Send HTTP request and return status code, status text, and body."""
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()

            response_line = await reader.readline()
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])
            status_text = parts[2] if len(parts) > 2 else ""

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                header_line = line.decode("utf-8").strip()
                if ":" in header_line:
                    key, value = header_line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            content_length = int(headers.get("content-length", 0))
            body = await reader.read(content_length)
            return status_code, status_text, body.decode("utf-8")
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_unhealthy_response_503(
        self,
        running_server_with_monitor: HealthServer,
        mock_health_monitor: MagicMock,
    ) -> None:
        """Test that unhealthy status returns 503."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.UNHEALTHY
        mock_state.consecutive_errors = 5
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        port = self._get_server_port(running_server_with_monitor)
        status_code, status_text, body = await self._send_request(
            port, "GET", "/health/ready"
        )

        assert status_code == 503
        assert status_text == "Service Unavailable"
        data = json.loads(body)
        assert data["status"] == "unhealthy"


class TestHealthServerErrorHandling:
    """Tests for error handling in health server."""

    @pytest.mark.asyncio
    async def test_handle_connection_timeout(self) -> None:
        """Test that TimeoutError in connection handling returns 408."""
        from unittest.mock import AsyncMock, patch

        server = HealthServer(host="127.0.0.1", port=0)

        # Mock _process_request to raise TimeoutError
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Patch _process_request to raise TimeoutError
        with patch.object(server, "_process_request", side_effect=TimeoutError()):
            await server._handle_connection(mock_reader, mock_writer)

        # Verify 408 response was sent
        mock_writer.write.assert_called()
        call_data = mock_writer.write.call_args[0][0]
        assert b"408" in call_data

    @pytest.mark.asyncio
    async def test_handle_connection_generic_exception(self) -> None:
        """Test that generic Exception in connection handling returns 500."""
        from unittest.mock import AsyncMock, patch

        mock_logger = MagicMock()
        server = HealthServer(host="127.0.0.1", port=0, logger=mock_logger)

        # Mock _process_request to raise a generic Exception
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Patch _process_request to raise a generic Exception
        with patch.object(
            server, "_process_request", side_effect=Exception("Test exception")
        ):
            await server._handle_connection(mock_reader, mock_writer)

        # Verify 500 response was sent
        mock_writer.write.assert_called()
        call_data = mock_writer.write.call_args[0][0]
        assert b"500" in call_data

        # Verify error was logged
        mock_logger.error.assert_called_with(
            "health_server_error", error="Test exception"
        )

    @pytest.mark.asyncio
    async def test_handle_request_error_without_logger(self) -> None:
        """Test that request errors are handled when no logger is configured."""
        server = HealthServer(host="127.0.0.1", port=0)

        # Create mock writer for error handling test
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = MagicMock(return_value=asyncio.Future())
        mock_writer.drain.return_value.set_result(None)

        # Test error handling without logger - should not raise
        error = Exception("Test error")
        await server._handle_request_error(mock_writer, error)

    @pytest.mark.asyncio
    async def test_request_error_logging(self) -> None:
        """Test that request errors are logged."""
        mock_logger = MagicMock()
        server = HealthServer(host="127.0.0.1", port=0, logger=mock_logger)

        await server.start()
        try:
            # Create mock writer for error handling test
            mock_writer = MagicMock()
            mock_writer.write = MagicMock()
            mock_writer.drain = MagicMock(return_value=asyncio.Future())
            mock_writer.drain.return_value.set_result(None)

            # Test error handling
            error = Exception("Test error")
            await server._handle_request_error(mock_writer, error)

            mock_logger.error.assert_called_with(
                "health_server_error", error="Test error"
            )
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_close_writer_handles_exceptions(self) -> None:
        """Test that _close_writer handles exceptions gracefully."""
        server = HealthServer(host="127.0.0.1", port=0)

        # Create mock writer that raises on close
        mock_writer = MagicMock()
        mock_writer.close = MagicMock(side_effect=Exception("Close error"))
        mock_writer.wait_closed = MagicMock(return_value=asyncio.Future())
        mock_writer.wait_closed.return_value.set_result(None)

        # Should not raise
        await server._close_writer(mock_writer)

    @pytest.mark.asyncio
    async def test_parse_request_line_valid(self) -> None:
        """Test parsing valid request line."""
        server = HealthServer(host="127.0.0.1", port=0)

        method, path = server._parse_request_line(b"GET /health HTTP/1.1\r\n")
        assert method == "GET"
        assert path == "/health"

    @pytest.mark.asyncio
    async def test_parse_request_line_invalid(self) -> None:
        """Test parsing invalid request line."""
        server = HealthServer(host="127.0.0.1", port=0)

        method, path = server._parse_request_line(b"INVALID\r\n")
        assert method is None
        assert path is None

    @pytest.mark.asyncio
    async def test_consume_headers(self) -> None:
        """Test that headers are consumed correctly."""
        server = HealthServer(host="127.0.0.1", port=0)

        # Create a mock reader with headers
        reader = asyncio.StreamReader()
        reader.feed_data(b"Content-Type: application/json\r\n")
        reader.feed_data(b"Content-Length: 0\r\n")
        reader.feed_data(b"\r\n")

        await server._consume_headers(reader)
        # Should complete without error


class TestRunHealthServer:
    """Tests for run_health_server function."""

    @pytest.mark.asyncio
    async def test_run_health_server_starts_and_stops(self) -> None:
        """Test run_health_server function starts and can be cancelled."""
        from bioetl.interfaces.http.health_server import run_health_server

        mock_logger = MagicMock()

        # Create task and cancel it after brief delay
        task = asyncio.create_task(
            run_health_server(
                host="127.0.0.1",
                port=0,
                logger=mock_logger,
            )
        )

        await asyncio.sleep(0.1)  # Let server start
        task.cancel()

        # The task catches CancelledError and performs cleanup,
        # so it may complete normally or raise CancelledError
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify server was started and stopped
        assert mock_logger.info.call_count >= 1

    @pytest.mark.asyncio
    async def test_run_health_server_with_monitor(self) -> None:
        """Test run_health_server with health monitor."""
        from bioetl.interfaces.http.health_server import run_health_server

        mock_monitor = MagicMock()
        mock_monitor.get_all_states.return_value = {}
        mock_logger = MagicMock()

        task = asyncio.create_task(
            run_health_server(
                host="127.0.0.1",
                port=0,
                health_monitor=mock_monitor,
                logger=mock_logger,
            )
        )

        await asyncio.sleep(0.1)
        task.cancel()

        # The task catches CancelledError and performs cleanup
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify server was started
        assert mock_logger.info.call_count >= 1


class TestHealthServerProviderStatuses:
    """Tests for provider status handling."""

    @pytest.fixture
    def mock_health_monitor(self) -> MagicMock:
        """Create a mock health monitor."""
        return MagicMock()

    def test_get_provider_statuses_without_monitor(self) -> None:
        """Test _get_provider_statuses without monitor returns empty dict."""
        server = HealthServer(host="127.0.0.1", port=0)
        result = server._get_provider_statuses()
        assert result == {}

    def test_get_provider_statuses_with_monitor(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test _get_provider_statuses returns formatted provider data."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.HEALTHY
        mock_state.consecutive_errors = 0
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        server = HealthServer(
            host="127.0.0.1", port=0, health_monitor=mock_health_monitor
        )
        result = server._get_provider_statuses()

        assert "chembl" in result
        assert result["chembl"]["status"] == "healthy"
        assert result["chembl"]["consecutive_errors"] == 0

    def test_get_overall_status_without_monitor(self) -> None:
        """Test _get_overall_status without monitor returns HEALTHY."""
        server = HealthServer(host="127.0.0.1", port=0)
        status = server._get_overall_status()
        assert status == HealthStatus.HEALTHY

    def test_get_overall_status_empty_states(
        self, mock_health_monitor: MagicMock
    ) -> None:
        """Test _get_overall_status with empty states returns HEALTHY."""
        mock_health_monitor.get_all_states.return_value = {}

        server = HealthServer(
            host="127.0.0.1", port=0, health_monitor=mock_health_monitor
        )
        status = server._get_overall_status()
        assert status == HealthStatus.HEALTHY
