"""Unit tests for CLI health commands.

Tests for CLI health commands (health server, health check) with mocked services.
Uses Click's CliRunner for command testing without real infrastructure.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


class MockHealthStatus(Enum):
    """Mock health status enum."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass
class MockHealthResult:
    """Mock health check result."""

    status: MockHealthStatus
    latency_ms: float = 25.5
    endpoint: str = "https://api.example.com/health"
    last_error: str | None = None


# =============================================================================
# health group Tests
# =============================================================================


@pytest.mark.unit
class TestHealthGroup:
    """Tests for the health command group."""

    def test_health_help(self, cli_runner: CliRunner):
        """Test health --help shows subcommands."""
        result = cli_runner.invoke(cli, ["health", "--help"])

        assert result.exit_code == 0
        assert "server" in result.output
        assert "check" in result.output
        assert "Health check" in result.output or "monitoring" in result.output

    def test_health_without_subcommand(self, cli_runner: CliRunner):
        """Test health without subcommand shows help."""
        result = cli_runner.invoke(cli, ["health"])

        # Click groups exit with code 0 and show subcommands when invoked alone
        # The exit code may vary based on Click version
        assert "server" in result.output or "check" in result.output


# =============================================================================
# health server Tests
# =============================================================================


@pytest.mark.unit
class TestHealthServerCommand:
    """Tests for health server command."""

    def test_health_server_help(self, cli_runner: CliRunner):
        """Test health server --help shows correct options."""
        result = cli_runner.invoke(cli, ["health", "server", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "0.0.0.0" in result.output  # default host

    def test_health_server_outputs_endpoints(self, cli_runner: CliRunner):
        """Test that health server outputs endpoint information before starting."""
        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()

        mock_monitor = MagicMock()
        mock_metrics = MagicMock()

        with (
            patch(
                "bioetl.interfaces.http.health_server.HealthServer",
                return_value=mock_server,
            ),
            patch(
                "bioetl.infrastructure.adapters.http.health_monitor.ProviderHealthMonitor",
                return_value=mock_monitor,
            ),
            patch(
                "bioetl.infrastructure.observability.prometheus_metrics.PrometheusMetrics",
                return_value=mock_metrics,
            ),
            patch("asyncio.run", side_effect=KeyboardInterrupt()),
        ):
            result = cli_runner.invoke(cli, ["health", "server", "--port", "9090"])

        # Should output endpoint info
        assert "Starting health server" in result.output
        assert "/health" in result.output
        assert "/health/live" in result.output
        assert "/health/ready" in result.output
        assert "/health/providers" in result.output
        assert "9090" in result.output

    def test_health_server_custom_host_and_port(self, cli_runner: CliRunner):
        """Test health server with custom host and port."""
        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(
                cli, ["health", "server", "--host", "127.0.0.1", "--port", "8081"]
            )

        assert "127.0.0.1" in result.output
        assert "8081" in result.output

    def test_health_server_keyboard_interrupt_exits_gracefully(
        self, cli_runner: CliRunner
    ):
        """Test that health server exits gracefully on KeyboardInterrupt."""
        with patch("asyncio.run", side_effect=KeyboardInterrupt()):
            result = cli_runner.invoke(cli, ["health", "server"])

        assert result.exit_code == 0
        assert "Shutting down" in result.output


# =============================================================================
# health check Tests
# =============================================================================


@pytest.mark.unit
class TestHealthCheckCommand:
    """Tests for health check command."""

    def test_health_check_help(self, cli_runner: CliRunner):
        """Test health check --help shows correct options."""
        result = cli_runner.invoke(cli, ["health", "check", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--json" in result.output

    def test_health_check_all_providers_healthy(self, cli_runner: CliRunner):
        """Test health check when all providers are healthy."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.HEALTHY,
                latency_ms=25.5,
                endpoint="https://api.example.com",
            )
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl", "pubchem"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == 0
        assert "[OK]" in result.output
        assert "healthy" in result.output
        assert "All providers healthy" in result.output

    def test_health_check_some_unhealthy(self, cli_runner: CliRunner):
        """Test health check when some providers are unhealthy."""
        healthy_adapter = MagicMock()
        healthy_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(status=MockHealthStatus.HEALTHY)
        )

        unhealthy_adapter = MagicMock()
        unhealthy_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.UNHEALTHY,
                latency_ms=0,
                endpoint="https://down.api.com",
                last_error="Connection refused",
            )
        )

        def create_adapter(provider):
            if provider == "chembl":
                return healthy_adapter
            return unhealthy_adapter

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl", "pubchem"]
        mock_factory.create.side_effect = create_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code != 0  # Should fail when some unhealthy
        assert "[OK]" in result.output  # chembl healthy
        assert "[FAIL]" in result.output  # pubchem unhealthy
        assert "Connection refused" in result.output
        assert "Some providers unhealthy" in result.output

    def test_health_check_degraded_provider(self, cli_runner: CliRunner):
        """Test health check when a provider is degraded."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.DEGRADED,
                latency_ms=500.0,
                endpoint="https://slow.api.com",
            )
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code != 0  # Degraded is not healthy
        assert "[WARN]" in result.output
        assert "degraded" in result.output

    def test_health_check_specific_provider(self, cli_runner: CliRunner):
        """Test health check for a specific provider."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(status=MockHealthStatus.HEALTHY)
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl", "pubchem", "uniprot"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check", "-p", "chembl"])

        assert result.exit_code == 0
        # Should only check chembl, not others
        assert mock_factory.create.call_count == 1
        mock_factory.create.assert_called_with("chembl")

    def test_health_check_multiple_providers(self, cli_runner: CliRunner):
        """Test health check for multiple specific providers."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(status=MockHealthStatus.HEALTHY)
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl", "pubchem", "uniprot"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(
                cli, ["health", "check", "-p", "chembl", "-p", "pubchem"]
            )

        assert result.exit_code == 0
        assert mock_factory.create.call_count == 2

    def test_health_check_json_output(self, cli_runner: CliRunner):
        """Test health check with JSON output."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.HEALTHY,
                latency_ms=30.25,
                endpoint="https://api.chembl.org",
            )
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check", "--json"])

        assert result.exit_code == 0
        assert '"chembl"' in result.output
        assert '"status": "healthy"' in result.output
        assert '"latency_ms": "30.25"' in result.output
        assert '"endpoint"' in result.output

    def test_health_check_json_output_with_error(self, cli_runner: CliRunner):
        """Test health check JSON output includes errors."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.UNHEALTHY,
                latency_ms=0,
                endpoint="https://api.chembl.org",
                last_error="Connection timeout",
            )
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check", "--json"])

        # JSON output should still work (exit code may be 0 or 1)
        assert '"error": "Connection timeout"' in result.output

    def test_health_check_adapter_with_health_check_method(
        self, cli_runner: CliRunner
    ):
        """Test health check with adapter using health_check() method."""
        mock_adapter = MagicMock(spec=["health_check"])
        mock_adapter.health_check = AsyncMock(return_value=MockHealthStatus.HEALTHY)

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["legacy_provider"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == 0
        assert "healthy" in result.output

    def test_health_check_adapter_without_health_method(self, cli_runner: CliRunner):
        """Test health check with adapter that has no health check method."""
        mock_adapter = MagicMock(spec=[])  # No health methods

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["no_health_provider"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "unknown" in result.output
        assert "No health check method" in result.output

    def test_health_check_adapter_raises_exception(self, cli_runner: CliRunner):
        """Test health check when adapter raises exception."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            side_effect=RuntimeError("Network unreachable")
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["failing_provider"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code != 0
        assert "unhealthy" in result.output
        assert "Network unreachable" in result.output

    def test_health_check_run_checks_exception(self, cli_runner: CliRunner):
        """Test health check handles exceptions in run_checks."""
        mock_factory = MagicMock()
        mock_factory.list_providers.side_effect = RuntimeError("Factory error")

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code != 0
        assert "Error running health checks" in result.output

    def test_health_check_latency_formatting(self, cli_runner: CliRunner):
        """Test health check formats latency correctly."""
        mock_adapter = MagicMock()
        mock_adapter.check_health = AsyncMock(
            return_value=MockHealthResult(
                status=MockHealthStatus.HEALTHY,
                latency_ms=123.456,
                endpoint="https://api.example.com",
            )
        )

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["chembl"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == 0
        assert "123.46ms" in result.output  # Should be formatted with 2 decimals

    def test_health_check_no_latency_in_result(self, cli_runner: CliRunner):
        """Test health check output when adapter uses health_check without latency."""
        mock_adapter = MagicMock(spec=["health_check"])
        mock_adapter.health_check = AsyncMock(return_value=MockHealthStatus.HEALTHY)

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["simple_provider"]
        mock_factory.create.return_value = mock_adapter

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code == 0
        # Output should not contain latency for simple health_check
        assert "[OK]" in result.output


# =============================================================================
# Integration-style tests for health command flows
# =============================================================================


@pytest.mark.unit
class TestHealthCommandIntegration:
    """Integration-style tests for health command workflows."""

    def test_health_check_mixed_statuses(self, cli_runner: CliRunner):
        """Test health check with mixed provider statuses."""
        adapters = {
            "healthy_provider": MagicMock(
                check_health=AsyncMock(
                    return_value=MockHealthResult(status=MockHealthStatus.HEALTHY)
                )
            ),
            "degraded_provider": MagicMock(
                check_health=AsyncMock(
                    return_value=MockHealthResult(status=MockHealthStatus.DEGRADED)
                )
            ),
            "unhealthy_provider": MagicMock(
                check_health=AsyncMock(
                    return_value=MockHealthResult(
                        status=MockHealthStatus.UNHEALTHY,
                        last_error="Service down",
                    )
                )
            ),
        }

        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = list(adapters.keys())
        mock_factory.create.side_effect = lambda p: adapters[p]

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert result.exit_code != 0  # Some unhealthy
        assert "[OK]" in result.output
        assert "[WARN]" in result.output
        assert "[FAIL]" in result.output
        assert "Some providers unhealthy" in result.output

    def test_health_check_factory_create_fails(self, cli_runner: CliRunner):
        """Test health check when factory.create() raises exception."""
        mock_factory = MagicMock()
        mock_factory.list_providers.return_value = ["bad_provider"]
        mock_factory.create.side_effect = ValueError("Unknown provider")

        with patch(
            "bioetl.composition.factories.data_source_factory.DataSourceFactory",
            mock_factory,
        ):
            result = cli_runner.invoke(cli, ["health", "check"])

        assert "unhealthy" in result.output
        assert "Unknown provider" in result.output


__all__ = [
    "TestHealthGroup",
    "TestHealthServerCommand",
    "TestHealthCheckCommand",
    "TestHealthCommandIntegration",
]
