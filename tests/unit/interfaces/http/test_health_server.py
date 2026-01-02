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
