"""Unit tests for health.py CLI commands.

Tests health check and health server CLI commands.
"""

from __future__ import annotations

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
            "chembl": {"status": "degraded", "latency_ms": "500.00", "endpoint": "/api"},
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
                cli, ["health", "check", "--provider", "chembl", "--provider", "pubchem"]
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
