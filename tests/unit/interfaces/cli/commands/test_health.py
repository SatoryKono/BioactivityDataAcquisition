"""Unit tests for health.py CLI commands.

Tests health check and health server CLI commands.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.exit_codes import ExitCode


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestHealthGroup:
    """Test the health command group."""

    def test_health_help_displays_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that health --help displays available subcommands."""
        result = cli_runner.invoke(cli, ["health", "--help"])

        assert result.exit_code == 0
        assert "server" in result.output
        assert "check" in result.output
        assert "Health check and monitoring operations" in result.output


class TestHealthServerCommand:
    """Test the health server subcommand."""

    def test_health_server_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that health server --help displays options."""
        result = cli_runner.invoke(cli, ["health", "server", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "0.0.0.0" in result.output  # default host
        assert "8080" in result.output  # default port

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_default_options(
        self,
        mock_metrics: MagicMock,
        mock_monitor: MagicMock,
        mock_server: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server with default options."""
        # Setup mocks - intercept before asyncio.run
        mock_server_instance = MagicMock()
        mock_server_instance.start = AsyncMock()
        mock_server_instance.stop = AsyncMock()
        mock_server.return_value = mock_server_instance

        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(cli, ["health", "server"])

        # Verify output
        assert "Starting health server on http://0.0.0.0:8080" in result.output
        assert "/health" in result.output
        assert "/health/live" in result.output
        assert "/health/ready" in result.output
        assert "/health/providers" in result.output
        assert result.exit_code == ExitCode.OK.value

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_custom_host_port(
        self,
        mock_metrics: MagicMock,
        mock_monitor: MagicMock,
        mock_server: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server with custom host and port."""
        mock_server_instance = MagicMock()
        mock_server_instance.start = AsyncMock()
        mock_server_instance.stop = AsyncMock()
        mock_server.return_value = mock_server_instance

        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(
                cli, ["health", "server", "--host", "127.0.0.1", "--port", "9090"]
            )

        assert "Starting health server on http://127.0.0.1:9090" in result.output
        assert result.exit_code == ExitCode.OK.value

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_keyboard_interrupt(
        self,
        mock_metrics: MagicMock,
        mock_monitor: MagicMock,
        mock_server: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server graceful shutdown on Ctrl+C."""
        mock_server_instance = MagicMock()
        mock_server_instance.start = AsyncMock()
        mock_server_instance.stop = AsyncMock()
        mock_server.return_value = mock_server_instance

        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(cli, ["health", "server"])

        assert "Shutting down..." in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_health_server_port_option_short_form(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that health server accepts -p short form for port."""
        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(
                cli, ["health", "server", "--host", "localhost", "-p", "8888"]
            )

        assert "Starting health server on http://localhost:8888" in result.output
        assert result.exit_code == ExitCode.OK.value


class TestHealthCheckCommand:
    """Test the health check subcommand."""

    def test_health_check_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that health check --help displays options."""
        result = cli_runner.invoke(cli, ["health", "check", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--json" in result.output

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_all_providers_healthy(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when all providers are healthy."""
        # Setup mock
        mock_factory.list_providers.return_value = ["chembl", "pubchem"]

        results = {
            "chembl": {"status": "healthy", "latency_ms": "10.50", "endpoint": "/api"},
            "pubchem": {"status": "healthy", "latency_ms": "15.30", "endpoint": "/pug"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "Running health checks..." in result.output
        assert "All providers healthy." in result.output
        assert result.exit_code == ExitCode.OK.value

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_some_unhealthy(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when some providers are unhealthy."""
        mock_factory.list_providers.return_value = ["chembl", "pubchem"]

        results = {
            "chembl": {"status": "healthy", "latency_ms": "10.50", "endpoint": "/api"},
            "pubchem": {"status": "unhealthy", "error": "Connection refused"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "Some providers unhealthy." in result.output
        assert result.exit_code == ExitCode.FAIL.value

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_degraded_status(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with degraded status."""
        mock_factory.list_providers.return_value = ["chembl"]

        results = {
            "chembl": {
                "status": "degraded",
                "latency_ms": "500.00",
                "endpoint": "/api",
            },
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "[WARN]" in result.output
        assert "Some providers unhealthy." in result.output
        assert result.exit_code == ExitCode.FAIL.value

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_json_output(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with JSON output."""
        mock_factory.list_providers.return_value = ["chembl"]

        results = {
            "chembl": {"status": "healthy", "latency_ms": "10.50", "endpoint": "/api"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check", "--json"])

        # JSON output should include structure
        assert '"chembl"' in result.output
        assert '"status": "healthy"' in result.output
        assert '"latency_ms": "10.50"' in result.output

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_specific_providers(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check for specific providers."""
        mock_factory.list_providers.return_value = ["chembl", "pubchem", "uniprot"]

        # Return result only for the requested providers
        results = {
            "chembl": {"status": "healthy", "latency_ms": "10.50", "endpoint": "/api"},
            "pubchem": {"status": "healthy", "latency_ms": "15.30", "endpoint": "/pug"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(
                cli,
                ["health", "check", "--provider", "chembl", "--provider", "pubchem"],
            )

        assert "Running health checks..." in result.output
        assert result.exit_code == ExitCode.OK.value

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_display_latency(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check displays latency in output."""
        mock_factory.list_providers.return_value = ["chembl"]

        results = {
            "chembl": {"status": "healthy", "latency_ms": "25.50", "endpoint": "/api"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "25.50ms" in result.output
        assert "[OK]" in result.output

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_display_error(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check displays error in output."""
        mock_factory.list_providers.return_value = ["chembl"]

        results = {
            "chembl": {"status": "unhealthy", "error": "Connection timeout"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "Connection timeout" in result.output
        assert "[FAIL]" in result.output

    def test_health_check_exception_handling(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check handles exceptions gracefully."""
        with patch("asyncio.run", side_effect=Exception("Unexpected error")):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "Error running health checks" in result.output
        assert result.exit_code == ExitCode.FAIL.value

    @patch("bioetl.composition.factories.data_source_factory.DataSourceFactory")
    def test_health_check_unknown_status(
        self,
        mock_factory: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with unknown status shows FAIL icon."""
        mock_factory.list_providers.return_value = ["chembl"]

        results = {
            "chembl": {"status": "unknown", "error": "No health check method"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "[FAIL]" in result.output
        assert "unknown" in result.output


@pytest.fixture
def mock_health_service():
    """Create a mock HealthService for testing."""
    from dataclasses import dataclass, field
    from datetime import UTC, datetime

    @dataclass
    class MockHealthResult:
        """Mock HealthResult for testing."""

        provider: str
        status: str
        latency_ms: float | None = None
        endpoint: str | None = None
        error: str | None = None

        @property
        def is_healthy(self) -> bool:
            return self.status == "healthy"

        @property
        def is_unhealthy(self) -> bool:
            return self.status in ("unhealthy", "unknown")

        def to_dict(self) -> dict:
            result = {"status": self.status}
            if self.latency_ms is not None:
                result["latency_ms"] = f"{self.latency_ms:.2f}"
            if self.endpoint:
                result["endpoint"] = self.endpoint
            if self.error:
                result["error"] = self.error
            return result

    @dataclass
    class MockHealthSummary:
        """Mock HealthCheckSummary for testing."""

        results: dict
        all_healthy: bool

        def to_dict(self) -> dict:
            return {name: result.to_dict() for name, result in self.results.items()}

    service = MagicMock()
    # Default healthy result
    default_result = MockHealthResult(
        provider="test_provider",
        status="healthy",
        latency_ms=25.5,
        endpoint="/api/status",
    )
    service.check_providers = AsyncMock(
        return_value=MockHealthSummary(
            results={"test_provider": default_result}, all_healthy=True
        )
    )
    # Store mock classes for test customization
    service._MockHealthResult = MockHealthResult
    service._MockHealthSummary = MockHealthSummary
    return service


class TestHealthCheckAsyncExecution:
    """Test the actual async execution of health check."""

    def test_health_check_with_check_health_method(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when adapter has check_health method."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="test_provider",
            status="healthy",
            latency_ms=25.5,
            endpoint="/api/status",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"test_provider": result_obj}, all_healthy=True
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == ExitCode.OK.value
        assert "[OK]" in result.output
        assert "test_provider" in result.output
        assert "25.50ms" in result.output

    def test_health_check_with_check_health_has_error(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when check_health result has error."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="test_provider",
            status="unhealthy",
            latency_ms=100.0,
            endpoint="/api/status",
            error="Connection timeout",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"test_provider": result_obj}, all_healthy=False
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == ExitCode.FAIL.value
        assert "Connection timeout" in result.output

    def test_health_check_with_health_check_method(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when adapter has health_check method (via service)."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="legacy_provider",
            status="healthy",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"legacy_provider": result_obj}, all_healthy=True
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == ExitCode.OK.value
        assert "[OK]" in result.output
        assert "legacy_provider" in result.output

    def test_health_check_adapter_no_health_method(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when adapter has no health check methods."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="no_health_provider",
            status="unknown",
            error="Adapter does not implement HealthCheckPort",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"no_health_provider": result_obj}, all_healthy=False
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == ExitCode.FAIL.value
        assert "unknown" in result.output

    def test_health_check_adapter_raises_exception(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check when adapter raises exception during check."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="failing_provider",
            status="unhealthy",
            error="Network unreachable",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"failing_provider": result_obj}, all_healthy=False
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == ExitCode.FAIL.value
        assert "unhealthy" in result.output
        assert "Network unreachable" in result.output

    def test_health_check_specific_provider_filter(
        self,
        mock_health_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check filters to specific providers."""
        MockHealthResult = mock_health_service._MockHealthResult
        MockHealthSummary = mock_health_service._MockHealthSummary

        result_obj = MockHealthResult(
            provider="chembl",
            status="healthy",
            latency_ms=10.0,
            endpoint="/api",
        )
        mock_health_service.check_providers = AsyncMock(
            return_value=MockHealthSummary(
                results={"chembl": result_obj}, all_healthy=True
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.health.get_health_service",
            return_value=mock_health_service,
        ):
            result = cli_runner.invoke(cli, ["health", "check", "--provider", "chembl"])

        assert result.exit_code == ExitCode.OK.value
        # check_providers should be called with provider filter
        mock_health_service.check_providers.assert_called_once_with(
            providers=["chembl"]
        )


class TestHealthServerAsyncExecution:
    """Test the actual async execution of health server."""

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_starts_and_stops(
        self,
        mock_metrics_cls: MagicMock,
        mock_monitor_cls: MagicMock,
        mock_server_cls: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server starts and stops correctly."""
        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Simulate CancelledError after first sleep to trigger shutdown
        async def cancelling_sleep(seconds: float) -> None:
            raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=cancelling_sleep):
            result = cli_runner.invoke(cli, ["health", "server"])

        # Verify server was started and stopped
        mock_server.start.assert_called_once()
        mock_server.stop.assert_called_once()
        assert "Health server stopped." in result.output

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_with_custom_options(
        self,
        mock_metrics_cls: MagicMock,
        mock_monitor_cls: MagicMock,
        mock_server_cls: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server passes custom host/port to HealthServer."""
        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        async def cancelling_sleep(seconds: float) -> None:
            raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=cancelling_sleep):
            cli_runner.invoke(
                cli,
                ["health", "server", "--host", "127.0.0.1", "--port", "9000"],
            )

        # Verify HealthServer was called with correct options
        mock_server_cls.assert_called_once()
        call_kwargs = mock_server_cls.call_args.kwargs
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 9000

    @patch("bioetl.interfaces.http.health_server.HealthServer")
    @patch("bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor")
    @patch("bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics")
    def test_health_server_creates_components(
        self,
        mock_metrics_cls: MagicMock,
        mock_monitor_cls: MagicMock,
        mock_server_cls: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test health server creates metrics and monitor."""
        mock_metrics = MagicMock()
        mock_metrics_cls.return_value = mock_metrics

        mock_monitor = MagicMock()
        mock_monitor_cls.return_value = mock_monitor

        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        async def cancelling_sleep(seconds: float) -> None:
            raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=cancelling_sleep):
            cli_runner.invoke(cli, ["health", "server"])

        # Verify components were created
        mock_metrics_cls.assert_called_once()
        mock_monitor_cls.assert_called_once_with(metrics=mock_metrics)
        mock_server_cls.assert_called_once_with(
            host="0.0.0.0",
            port=8080,
            health_monitor=mock_monitor,
        )


class TestHealthCheckEdgeCases:
    """Test edge cases for health check command."""

    def test_health_check_empty_providers(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with empty provider list."""
        with patch("asyncio.run", return_value={}):
            result = cli_runner.invoke(cli, ["health", "check"])

        # Should show "All providers healthy" even with no providers
        assert "All providers healthy" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_health_check_with_multiple_provider_flags(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with multiple --provider flags."""
        results = {
            "chembl": {"status": "healthy", "latency_ms": "10.00"},
            "pubchem": {"status": "healthy", "latency_ms": "15.00"},
        }

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(
                cli,
                [
                    "health",
                    "check",
                    "-p",
                    "chembl",
                    "-p",
                    "pubchem",
                ],
            )

        assert "Running health checks..." in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_health_check_short_provider_option(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test health check with -p short form for provider."""
        results = {"chembl": {"status": "healthy", "latency_ms": "10.00"}}

        with patch("asyncio.run", return_value=results):
            result = cli_runner.invoke(cli, ["health", "check", "-p", "chembl"])

        assert "Running health checks..." in result.output
        assert result.exit_code == ExitCode.OK.value
