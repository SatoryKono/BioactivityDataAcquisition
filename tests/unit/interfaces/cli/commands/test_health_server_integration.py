"""Unit tests for health server CLI integration.

Tests the health_server_integration module that provides utilities
for running the health server alongside long-running CLI operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestHealthServerContext:
    """Test the health_server_context async context manager."""

    @pytest.mark.asyncio
    async def test_context_disabled_yields_none(self) -> None:
        """Test that disabled context yields None without starting server."""
        async with health_server_context(enabled=False) as server:
            assert server is None

    @pytest.mark.asyncio
    @patch("bioetl.composition.entrypoints.get_health_server_dependencies")
    @patch("bioetl.interfaces.http.health_server.HealthServer")
    async def test_context_enabled_starts_and_stops_server(
        self,
        mock_server_cls: MagicMock,
        mock_get_deps: MagicMock,
    ) -> None:
        """Test that enabled context starts and stops the server."""
        # Setup mocks
        mock_deps = MagicMock()
        mock_deps.health_monitor = MagicMock()
        mock_get_deps.return_value = mock_deps

        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        async with health_server_context(enabled=True, port=8080) as server:
            assert server is mock_server
            mock_server.start.assert_called_once()

        mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.composition.entrypoints.get_health_server_dependencies")
    @patch("bioetl.interfaces.http.health_server.HealthServer")
    async def test_context_stops_server_on_exception(
        self,
        mock_server_cls: MagicMock,
        mock_get_deps: MagicMock,
    ) -> None:
        """Test that server is stopped even when exception occurs."""
        mock_deps = MagicMock()
        mock_get_deps.return_value = mock_deps

        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        with pytest.raises(RuntimeError):
            async with health_server_context(enabled=True):
                raise RuntimeError("Test error")

        mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.composition.entrypoints.get_health_server_dependencies")
    @patch("bioetl.interfaces.http.health_server.HealthServer")
    async def test_context_custom_host_port(
        self,
        mock_server_cls: MagicMock,
        mock_get_deps: MagicMock,
    ) -> None:
        """Test that custom host and port are passed to server."""
        mock_deps = MagicMock()
        mock_deps.health_monitor = MagicMock()
        mock_get_deps.return_value = mock_deps

        mock_server = MagicMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_server_cls.return_value = mock_server

        async with health_server_context(enabled=True, host="127.0.0.1", port=9090):
            # Verify server was created with correct host and port
            mock_server_cls.assert_called_once()
            call_kwargs = mock_server_cls.call_args.kwargs
            assert call_kwargs["host"] == "127.0.0.1"
            assert call_kwargs["port"] == 9090
            assert call_kwargs["health_monitor"] is mock_deps.health_monitor


class TestEchoHealthServerInfo:
    """Test the echo_health_server_info function."""

    def test_echo_when_enabled(self) -> None:
        """Test that info is echoed when health server is enabled."""

        # Use click's echo with standalone mode to capture output
        @click.command()
        def test_cmd() -> None:
            echo_health_server_info(True, 8080)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "Health server: http://127.0.0.1:8080/health" in result.output

    def test_no_echo_when_disabled(self) -> None:
        """Test that nothing is echoed when health server is disabled."""

        @click.command()
        def test_cmd() -> None:
            echo_health_server_info(False, 8080)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.output == ""

    def test_echo_custom_port(self) -> None:
        """Test that custom port is displayed in output."""

        @click.command()
        def test_cmd() -> None:
            echo_health_server_info(True, 9090)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "Health server: http://127.0.0.1:9090/health" in result.output


class TestRunCommandHealthServerOptions:
    """Test health server options in run command."""

    def test_run_help_shows_health_server_options(self, cli_runner: CliRunner) -> None:
        """Test that run --help displays health server options."""
        result = cli_runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "--health-server" in result.output
        assert "--no-health-server" in result.output
        assert "--health-port" in result.output
        assert "8080" in result.output  # default port


class TestRunAllCommandHealthServerOptions:
    """Test health server options in run-all command."""

    def test_run_all_help_shows_health_server_options(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that run-all --help displays health server options."""
        result = cli_runner.invoke(cli, ["run-all", "--help"])

        assert result.exit_code == 0
        assert "--health-server" in result.output
        assert "--no-health-server" in result.output
        assert "--health-port" in result.output


class TestRunCompositeCommandHealthServerOptions:
    """Test health server options in run-composite command."""

    def test_run_composite_help_shows_health_server_options(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that run-composite --help displays health server options."""
        result = cli_runner.invoke(cli, ["run-composite", "--help"])

        assert result.exit_code == 0
        assert "--health-server" in result.output
        assert "--no-health-server" in result.output
        assert "--health-port" in result.output


class TestDefaultHealthServerPort:
    """Test the default health server port constant."""

    def test_default_port_is_8080(self) -> None:
        """Test that default health server port is 8080."""
        assert DEFAULT_HEALTH_SERVER_PORT == 8080
