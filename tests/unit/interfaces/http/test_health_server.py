"""Tests for HTTP health server."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.types import HealthStatus, RunID, RunType
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.types import HealthResponse
from tests.helpers.control_plane import InMemoryRunManifestStore


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

        assert server.uptime_seconds == pytest.approx(0.0)

        await server.start()
        assert server._start_time is not None
        server._start_time -= 0.1
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

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server(self) -> AsyncGenerator[HealthServer, None]:
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

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_health_endpoint(self, running_server: HealthServer) -> None:
        """Test /health endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "server" in data["checks"]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_healthz_endpoint(self, running_server: HealthServer) -> None:
        """Test /healthz endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/healthz")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_liveness_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/live endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health/live")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "server" in data["checks"]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_readiness_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/ready endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health/ready")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_providers_endpoint(self, running_server: HealthServer) -> None:
        """Test /health/providers endpoint via HTTP."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(
            port, "GET", "/health/providers"
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio(loop_scope="module")
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

    @pytest.mark.asyncio(loop_scope="module")
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

    @pytest.mark.asyncio(loop_scope="module")
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

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_query_string_stripped(
        self, running_server: HealthServer
    ) -> None:
        """Test that query strings are stripped from path."""
        port = self._get_server_port(running_server)
        status_code, _, body = await self._send_request(port, "GET", "/health?foo=bar")

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "healthy"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_empty_request(self, running_server: HealthServer) -> None:
        """Test handling of empty request."""
        port = self._get_server_port(running_server)
        _reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            # Send empty request and close
            writer.write_eof()
            await writer.drain()
            # Should not raise, server handles gracefully
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_http_incomplete_headers_timeout(
        self, running_server: HealthServer
    ) -> None:
        """Test that incomplete headers return 408 instead of hanging forever."""
        port = self._get_server_port(running_server)
        original_timeout = running_server._header_line_timeout_seconds
        running_server._header_line_timeout_seconds = 0.01
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            writer.write(b"GET /health HTTP/1.1\r\nHost: localhost\r\n")
            await writer.drain()

            response_line = await asyncio.wait_for(reader.readline(), timeout=1.0)
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])

            assert status_code == 408
        finally:
            running_server._header_line_timeout_seconds = original_timeout
            writer.close()
            await writer.wait_closed()


class TestHealthServerQuarantineExplorer:
    """Tests for /ops/quarantine/* explorer endpoints."""

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_without_quarantine(
        self,
    ) -> AsyncGenerator[HealthServer, None]:
        """Start server without quarantine service."""
        server = HealthServer(host="127.0.0.1", port=0)
        await server.start()
        yield server
        await server.stop()

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_with_quarantine(
        self,
    ) -> AsyncGenerator[tuple[HealthServer, MagicMock], None]:
        """Start server with mocked quarantine service."""
        service = MagicMock()
        service.list_filtered_records = AsyncMock(
            return_value={"items": [], "total": 0, "limit": 50, "offset": 0}
        )
        service.get_filtered_stats = AsyncMock(
            return_value={
                "total": 0,
                "by_reason_code": [],
                "by_field": [],
                "by_reason_signature": [],
                "bronze_records": 0,
                "reject_ratio": 0.0,
            }
        )
        service.get_filtered_filter_options = AsyncMock(
            return_value={
                "pipelines": ["chembl_activity"],
                "run_types": ["incremental"],
                "reason_codes": ["missing_required_field"],
                "fields": ["canonical_smiles"],
                "run_ids": ["run-1"],
            }
        )
        service.get_filtered_record = AsyncMock(return_value=None)

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            quarantine_service=service,
        )
        await server.start()
        yield server, service
        await server.stop()

    @staticmethod
    def _get_server_port(server: HealthServer) -> int:
        """Get the actual port of the running server."""
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(
        self, port: int, method: str, path: str
    ) -> tuple[int, str, str]:
        """Send request and return status code, status text, and body."""
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

    @pytest.mark.asyncio(loop_scope="module")
    async def test_records_endpoint_requires_quarantine_service(
        self,
        running_server_without_quarantine: HealthServer,
    ) -> None:
        """Explorer endpoints should return 503 when service is not configured."""
        port = self._get_server_port(running_server_without_quarantine)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-records?pipeline=chembl_activity",
        )

        assert status_code == 503
        assert status_text == "Quarantine explorer unavailable"
        assert "Quarantine explorer unavailable" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_records_endpoint_requires_pipeline_scope(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """List endpoint should reject unscoped pipeline reads."""
        server, service = running_server_with_quarantine
        port = self._get_server_port(server)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-records?limit=10&offset=0",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body
        service.list_filtered_records.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_records_endpoint_delegates_to_quarantine_service(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """List endpoint should pass query filters to service call."""
        server, service = running_server_with_quarantine
        port = self._get_server_port(server)
        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-records?"
            "pipeline=chembl_activity&run_type=incremental&reason_code=missing_required_field&"
            "field=canonical_smiles&run_id=run-1&payload_hash=sha256%3Atest&"
            "from=2026-04-01T00%3A00%3A00Z&to=2026-04-02T00%3A00%3A00Z&"
            "limit=25&offset=5&sort=ingestion_ts_desc",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["total"] == 0
        service.list_filtered_records.assert_awaited_once_with(
            pipeline="chembl_activity",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash="sha256:test",
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
            limit=25,
            offset=5,
            sort="ingestion_ts_desc",
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_stats_endpoint_delegates_to_quarantine_service_and_returns_shape(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """Stats endpoint should expose the zero-reject contract used by Grafana."""
        server, service = running_server_with_quarantine
        port = self._get_server_port(server)
        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-stats?"
            "pipeline=chembl_activity&run_type=incremental&reason_code=missing_required_field&"
            "field=canonical_smiles&run_id=run-1&from=2026-04-01T00%3A00%3A00Z&"
            "to=2026-04-02T00%3A00%3A00Z",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data == {
            "total": 0,
            "by_reason_code": [],
            "by_field": [],
            "by_reason_signature": [],
            "bronze_records": 0,
            "reject_ratio": 0.0,
        }
        service.get_filtered_stats.assert_awaited_once_with(
            pipeline="chembl_activity",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash=None,
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_stats_endpoint_requires_pipeline_scope(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """Stats endpoint should reject unscoped pipeline reads."""
        server, service = running_server_with_quarantine
        port = self._get_server_port(server)

        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-stats?reason_code=missing_required_field",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body
        service.get_filtered_stats.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_filter_options_endpoint_requires_pipeline_scope(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """Filter-options endpoint should reject unscoped pipeline reads."""
        server, service = running_server_with_quarantine
        port = self._get_server_port(server)

        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filter-options?run_type=incremental",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body
        service.get_filtered_filter_options.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_record_detail_endpoint_returns_404(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """Detail endpoint should return 404 when hash is not found."""
        server, service = running_server_with_quarantine
        service.get_filtered_record = AsyncMock(return_value=None)
        port = self._get_server_port(server)

        status_code, status_text, _ = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-record/sha256%3Amissing?pipeline=chembl_activity",
        )

        assert status_code == 404
        assert status_text == "Not Found"
        service.get_filtered_record.assert_awaited_once_with(
            payload_hash="sha256:missing",
            pipeline="chembl_activity",
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_stats_endpoint_returns_500_when_service_crashes(
        self,
        running_server_with_quarantine: tuple[HealthServer, MagicMock],
    ) -> None:
        """Unexpected quarantine service errors must return HTTP 500."""
        server, service = running_server_with_quarantine
        service.get_filtered_stats = AsyncMock(side_effect=AssertionError("boom"))
        port = self._get_server_port(server)

        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/quarantine/filtered-stats?pipeline=chembl_activity",
        )

        assert status_code == 500
        assert status_text == "Internal Server Error"
        assert "Internal Server Error" in body


class TestHealthServerControlPlaneSelector:
    """Tests for /ops/control-plane/* selector helper endpoints."""

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_without_run_catalog(
        self,
    ) -> AsyncGenerator[HealthServer, None]:
        """Start server without control-plane run catalog."""
        server = HealthServer(host="127.0.0.1", port=0)
        await server.start()
        yield server
        await server.stop()

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_with_run_catalog(
        self,
    ) -> AsyncGenerator[tuple[HealthServer, InMemoryRunManifestStore], None]:
        """Start server with an in-memory control-plane run catalog."""
        manifest_store = InMemoryRunManifestStore()
        created_at = datetime(2026, 5, 12, 8, 21, tzinfo=UTC)
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-1",
                execution_fingerprint="fingerprint-1",
                schema_version="1.0",
                created_at=created_at,
                run_id=RunID(uuid4()),
                run_type=RunType.INCREMENTAL,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                launch_context={"limit": 10},
                runtime_config={"run_type": "incremental"},
                resolved_config={"pipeline_name": "chembl_activity"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="abc1234",
                    config_hash="deadbeef",
                ),
            )
        )
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-2",
                execution_fingerprint="fingerprint-2",
                schema_version="1.0",
                created_at=created_at,
                run_id=RunID(uuid4()),
                run_type=RunType.BACKFILL,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                launch_context={"limit": 10},
                runtime_config={"run_type": "backfill"},
                resolved_config={"pipeline_name": "chembl_activity"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="def5678",
                    config_hash="feedface",
                ),
            )
        )
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-3",
                execution_fingerprint="fingerprint-3",
                schema_version="1.0",
                created_at=created_at,
                run_id=RunID(uuid4()),
                run_type=RunType.INCREMENTAL,
                pipeline_name="pubchem_compound",
                provider="pubchem",
                entity="compound",
                launch_context={"limit": 10},
                runtime_config={"run_type": "incremental"},
                resolved_config={"pipeline_name": "pubchem_compound"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="ghi9012",
                    config_hash="cafebabe",
                ),
            )
        )

        server = HealthServer(
            host="127.0.0.1",
            port=0,
            run_manifest_port=manifest_store,
        )
        await server.start()
        yield server, manifest_store
        await server.stop()

    @staticmethod
    def _get_server_port(server: HealthServer) -> int:
        """Get the actual port of the running server."""
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(
        self, port: int, method: str, path: str
    ) -> tuple[int, str, str]:
        """Send request and return status code, status text, and body."""
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

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_requires_run_catalog(
        self,
        running_server_without_run_catalog: HealthServer,
    ) -> None:
        """Selector endpoint should return 503 when run catalog is not configured."""
        port = self._get_server_port(running_server_without_run_catalog)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?dimension=run_id&pipeline=chembl_activity",
        )

        assert status_code == 503
        assert status_text == "Control-plane selector catalog unavailable"
        assert "Control-plane selector catalog unavailable" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_requires_pipeline_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should reject unscoped control-plane reads."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?dimension=run_id",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_filters_run_ids_by_pipeline_and_run_type(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should expose exact run IDs from persisted manifests."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_incremental_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.pipeline_name == "chembl_activity"
            and manifest.run_type == RunType.INCREMENTAL
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&pipeline=chembl_activity&run_type=incremental",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["pipeline"] == "chembl_activity"
        assert data["run_type"] == ["incremental"]
        assert data["run_ids"] == expected_incremental_ids

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_returns_latest_manifest_for_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should resolve latest persisted manifest for scope."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "latest_manifest_for_scope"
        assert rows["manifest_id"] == "manifest-2"
        assert rows["pipeline name"] == "chembl_activity"
        assert rows["run_id"]
        assert rows["pipelineversion"] == "1.0.0"
        assert rows["git commit hash"] == "def5678"
        assert rows["config hash"] == "feedface"
        assert rows["execution fingerprint"] == "fingerprint-2"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_prefers_selected_run_id(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should resolve exact manifest when run_id is selected."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        selected_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-1"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            f"pipeline=chembl_activity&run_id={selected_manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "selected_run_id"
        assert rows["manifest_id"] == "manifest-1"
        assert rows["run_id"] == str(selected_manifest.run_id)
        assert rows["execution fingerprint"] == "fingerprint-1"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_requires_pipeline_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should reject unscoped reads."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_rejects_unknown_dimension(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should fail closed for unsupported filter dimensions."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=manifest_id&pipeline=chembl_activity",
        )

        assert status_code == 400
        assert status_text == "Unsupported control-plane filter dimension: manifest_id"
        assert "Unsupported control-plane filter dimension: manifest_id" in body


class TestHealthServerWithMonitor:
    """Tests for health server with health monitor configured."""

    @pytest.fixture
    def mock_health_monitor(self) -> MagicMock:
        """Create a mock health monitor."""
        monitor = MagicMock()
        monitor.get_all_states.return_value = {}
        return monitor

    @pytest.mark.asyncio
    async def test_unhealthy_response_503(
        self,
        mock_health_monitor: MagicMock,
    ) -> None:
        """Test that unhealthy status returns 503 via real HTTP connection."""
        mock_state = MagicMock()
        mock_state.status = HealthStatus.UNHEALTHY
        mock_state.consecutive_errors = 5
        mock_health_monitor.get_all_states.return_value = {"chembl": mock_state}

        server = HealthServer(
            host="127.0.0.1", port=0, health_monitor=mock_health_monitor
        )
        await server.start()
        try:
            assert server._server is not None
            sockets = server._server.sockets
            assert sockets is not None
            port = int(sockets[0].getsockname()[1])

            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            try:
                writer.write(b"GET /health/ready HTTP/1.1\r\nHost: localhost\r\n\r\n")
                await writer.drain()

                response_line = await reader.readline()
                parts = response_line.decode("utf-8").strip().split(" ", 2)
                status_code = int(parts[1])
                status_text = parts[2] if len(parts) > 2 else ""

                headers: dict[str, str] = {}
                while True:
                    line = await reader.readline()
                    if line in (b"\r\n", b"\n", b""):
                        break
                    header_line = line.decode("utf-8").strip()
                    if ":" in header_line:
                        key, value = header_line.split(":", 1)
                        headers[key.strip().lower()] = value.strip()

                content_length = int(headers.get("content-length", 0))
                body = (await reader.read(content_length)).decode("utf-8")
            finally:
                writer.close()
                await writer.wait_closed()

            assert status_code == 503
            assert status_text == "Service Unavailable"
            data = json.loads(body)
            assert data["status"] == "unhealthy"
        finally:
            await server.stop()


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

        # Mock _process_request to raise a typed request-processing exception
        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Patch _process_request to raise typed exception from allowlist
        with patch.object(
            server, "_process_request", side_effect=RuntimeError("Test exception")
        ):
            await server._handle_connection(mock_reader, mock_writer)

        # Verify 500 response was sent
        mock_writer.write.assert_called()
        call_data = mock_writer.write.call_args[0][0]
        assert b"500" in call_data

        # Verify error was logged
        mock_logger.error.assert_called_with(
            "health_server_error",
            error="Test exception",
            error_type="RuntimeError",
            reason="request_processing_failed",
            reason_code="HEALTH_REQUEST_PROCESSING_FAILED",
        )

    @pytest.mark.asyncio
    async def test_handle_connection_unexpected_exception(self) -> None:
        """Unexpected request exceptions should also return HTTP 500."""
        from unittest.mock import AsyncMock, patch

        mock_logger = MagicMock()
        server = HealthServer(host="127.0.0.1", port=0, logger=mock_logger)

        mock_reader = AsyncMock()
        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with patch.object(
            server,
            "_process_request",
            side_effect=AssertionError("Unexpected exception"),
        ):
            await server._handle_connection(mock_reader, mock_writer)

        mock_writer.write.assert_called()
        call_data = mock_writer.write.call_args[0][0]
        assert b"500" in call_data

        mock_logger.error.assert_called_with(
            "health_server_error",
            error="Unexpected exception",
            error_type="AssertionError",
            reason="request_processing_failed",
            reason_code="HEALTH_REQUEST_PROCESSING_FAILED",
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
        error = RuntimeError("Test error")
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
            error = RuntimeError("Test error")
            await server._handle_request_error(mock_writer, error)

            mock_logger.error.assert_called_with(
                "health_server_error",
                error="Test error",
                error_type="RuntimeError",
                reason="request_processing_failed",
                reason_code="HEALTH_REQUEST_PROCESSING_FAILED",
            )
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_close_writer_handles_exceptions(self) -> None:
        """Test that _close_writer handles exceptions gracefully."""
        server = HealthServer(host="127.0.0.1", port=0)

        # Create mock writer that raises on close
        mock_writer = MagicMock()
        mock_writer.close = MagicMock(side_effect=OSError("Close error"))
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

        for _ in range(20):
            if mock_logger.info.call_count >= 1:
                break
            await asyncio.sleep(0)
        task.cancel()

        # run_health_server re-raises cancellation after cleanup.
        with pytest.raises(asyncio.CancelledError):
            await task

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

        for _ in range(20):
            if mock_logger.info.call_count >= 1:
                break
            await asyncio.sleep(0)
        task.cancel()

        # run_health_server re-raises cancellation after cleanup.
        with pytest.raises(asyncio.CancelledError):
            await task

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
