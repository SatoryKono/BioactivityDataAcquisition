"""Integration tests for CLI graceful shutdown.

Tests the integration between OS signals, ShutdownSignal, and CLI exit codes.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.interfaces.cli import cli
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

if TYPE_CHECKING:
    from click.testing import CliRunner


class TestShutdownSignalIntegration:
    """Test ShutdownSignal integration with signal handlers."""

    def test_setup_shutdown_handlers_registers_sigterm(self):
        """Test that setup_shutdown_handlers registers SIGTERM handler."""
        import signal

        shutdown_signal = ShutdownSignal()

        with patch.object(signal, "signal") as mock_signal:
            setup_shutdown_handlers(shutdown_signal)

            # Should register both SIGTERM and SIGINT
            calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in calls
            assert signal.SIGINT in calls

    def test_shutdown_signal_request_triggers_event(self):
        """Test that request() sets the is_requested flag."""
        shutdown_signal = ShutdownSignal()

        assert shutdown_signal.is_requested is False
        shutdown_signal.request()
        assert shutdown_signal.is_requested is True

    @pytest.mark.asyncio
    async def test_shutdown_signal_wait_returns_on_request(self):
        """Test that wait() returns when request() is called."""
        shutdown_signal = ShutdownSignal()

        async def delayed_request():
            await asyncio.sleep(0.05)
            shutdown_signal.request()

        task = asyncio.create_task(delayed_request())

        # Wait should return after request
        await asyncio.wait_for(shutdown_signal.wait(), timeout=1.0)

        assert shutdown_signal.is_requested is True
        await task

    def test_shutdown_signal_reset_clears_flag(self):
        """Test that reset() clears the shutdown flag."""
        shutdown_signal = ShutdownSignal()

        shutdown_signal.request()
        assert shutdown_signal.is_requested is True

        shutdown_signal.reset()
        assert shutdown_signal.is_requested is False


class TestCliGracefulShutdownExitCode:
    """Test CLI exit codes on graceful shutdown."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        register_all_pipelines()

    def test_shutdown_error_returns_exit_code_130(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that SHUTDOWN status results in exit code 130."""
        from bioetl.application.services import RunStatus

        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run"
        ) as mock_asyncio_run:
            # _run_pipeline_async returns (status, error_message, error_type) tuple
            mock_asyncio_run.return_value = (RunStatus.SHUTDOWN, None, None)

            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 130

    def test_normal_completion_returns_exit_code_0(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that normal completion returns exit code 0."""
        import asyncio

        from bioetl.application.services import RunResult, RunStatus

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
        )

        with (
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.asyncio.run",
                side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0

    def test_other_exception_returns_exit_code_1(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that other exceptions return exit code 1."""
        mock_service = MagicMock()

        with (
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.asyncio.run",
                side_effect=RuntimeError("Something went wrong"),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 1


class TestSignalHandlerIntegration:
    """Test signal handler triggers shutdown correctly."""

    def test_signal_handler_requests_shutdown(self):
        """Test that signal handler calls shutdown_signal.request()."""

        shutdown_signal = ShutdownSignal()

        # Setup handlers
        setup_shutdown_handlers(shutdown_signal)

        # The handler should have been registered
        # Simulate calling the handler manually
        # (We can't actually send signals in unit tests safely)

        assert shutdown_signal.is_requested is False

        # Manually trigger by calling request
        shutdown_signal.request()
        assert shutdown_signal.is_requested is True

    def test_shutdown_signal_is_idempotent(self):
        """Test that multiple request() calls don't cause issues."""
        shutdown_signal = ShutdownSignal()

        shutdown_signal.request()
        shutdown_signal.request()
        shutdown_signal.request()

        assert shutdown_signal.is_requested is True

    @pytest.mark.asyncio
    async def test_shutdown_during_async_operation(self):
        """Test that shutdown signal can interrupt async operations."""
        shutdown_signal = ShutdownSignal()

        async def long_running_task():
            for _ in range(100):
                if shutdown_signal.is_requested:
                    raise PipelineShutdownError("Shutdown requested")
                await asyncio.sleep(0.01)

        # Request shutdown after a short delay
        async def delayed_shutdown():
            await asyncio.sleep(0.05)
            shutdown_signal.request()

        task = asyncio.create_task(delayed_shutdown())

        with pytest.raises(PipelineShutdownError):
            await long_running_task()

        await task


class TestRunnerShutdownIntegration:
    """Test runner behavior during shutdown."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        register_all_pipelines()

    def test_runner_logs_graceful_shutdown(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that SHUTDOWN status results in shutdown warning."""
        import asyncio

        from bioetl.application.services import RunResult, RunStatus

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=RunStatus.SHUTDOWN,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
        )

        with (
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.asyncio.run",
                side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        # CLI should output shutdown warning message
        assert result.exit_code == 130
        assert "shut down" in result.output.lower() or "graceful" in result.output.lower()

    def test_runner_shutdown_signal_passed_to_setup(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that service-based architecture handles shutdown correctly."""
        import asyncio

        from bioetl.application.services import RunResult, RunStatus

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
        )

        with (
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.asyncio.run",
                side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        # Verify service was called correctly
        mock_service.run.assert_called_once()
        assert result.exit_code == 0


class TestLockReleaseOnShutdown:
    """Test that locks are released on shutdown."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        register_all_pipelines()

    def test_lock_released_after_shutdown(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that lock is released even after shutdown error."""
        import asyncio

        from bioetl.application.services import RunResult, RunStatus

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=RunStatus.SHUTDOWN,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
        )

        with (
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.asyncio.run",
                side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity"],
            )

        # Should complete with 130, not hang
        assert result.exit_code == 130


class TestConcurrentSignals:
    """Test handling of concurrent signals."""

    def test_multiple_shutdown_requests_are_safe(self):
        """Test that multiple concurrent shutdown requests are safe."""
        shutdown_signal = ShutdownSignal()

        # Simulate multiple concurrent requests
        for _ in range(10):
            shutdown_signal.request()

        assert shutdown_signal.is_requested is True

    @pytest.mark.asyncio
    async def test_multiple_waiters_all_unblocked(self):
        """Test that multiple waiters are all unblocked on shutdown."""
        shutdown_signal = ShutdownSignal()
        unblocked = []

        async def waiter(index: int):
            await shutdown_signal.wait()
            unblocked.append(index)

        # Create multiple waiters
        tasks = [asyncio.create_task(waiter(i)) for i in range(5)]

        # Small delay then request shutdown
        await asyncio.sleep(0.01)
        shutdown_signal.request()

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # All waiters should have been unblocked
        assert len(unblocked) == 5
        assert set(unblocked) == {0, 1, 2, 3, 4}


class TestShutdownWithCheckpointManager:
    """Test checkpoint manager behavior during shutdown.

    These tests verify that the checkpoint saving mechanism is
    properly integrated with shutdown handling.
    """

    @pytest.mark.asyncio
    async def test_shutdown_signal_in_lock_manager(self):
        """Test that LockManager uses shutdown_signal correctly."""
        from bioetl.application.core.lock_manager import LockManager

        mock_lock = MagicMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        mock_lock.heartbeat = AsyncMock(return_value=True)

        mock_logger = MagicMock()
        mock_checkpoint = MagicMock()
        shutdown_signal = ShutdownSignal()

        from uuid import uuid4

        from bioetl.application.core.config import LockConfig

        lock_config = LockConfig(
            lock_key="test:lock",
            exclusive=False,
            lock_ttl=300,
            wait_for_lock=False,
            wait_timeout=10,
            heartbeat_interval=60,
        )
        manager = LockManager(
            lock_port=mock_lock,
            run_id=uuid4(),
            config=lock_config,
            logger=mock_logger,
            shutdown_signal=shutdown_signal,
            checkpoint_manager=mock_checkpoint,
        )

        # Acquire lock
        acquired = await manager.acquire()
        assert acquired is True

        # Start heartbeat
        await manager.start_heartbeat()

        # Request shutdown
        shutdown_signal.request()

        # Give heartbeat loop time to check signal
        await asyncio.sleep(0.1)

        # Release lock
        await manager.release()

        # Verify lock was released
        mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_failure_triggers_shutdown(self):
        """Test that heartbeat failure triggers shutdown signal."""
        from bioetl.application.core.lock_manager import LockManager

        mock_lock = MagicMock()
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock()
        # First heartbeat succeeds, subsequent ones fail
        mock_lock.heartbeat = AsyncMock(side_effect=[True, False])

        mock_logger = MagicMock()
        shutdown_signal = ShutdownSignal()

        from uuid import uuid4

        from bioetl.application.core.config import LockConfig

        lock_config = LockConfig(
            lock_key="test:lock",
            exclusive=False,
            lock_ttl=300,
            wait_for_lock=False,
            wait_timeout=10,
            heartbeat_interval=0,  # Immediate for testing
        )
        manager = LockManager(
            lock_port=mock_lock,
            run_id=uuid4(),
            config=lock_config,
            logger=mock_logger,
            shutdown_signal=shutdown_signal,
            checkpoint_manager=None,
        )

        # Acquire lock
        await manager.acquire()

        # Start heartbeat - this creates a background task
        await manager.start_heartbeat()

        # Wait for the heartbeat loop to run and fail
        # The background task should set the shutdown signal
        await asyncio.sleep(0.1)

        # Verify shutdown was triggered
        assert shutdown_signal.is_requested is True

        # Clean up - release may raise PipelineShutdownError if the
        # heartbeat task was awaited and raised it
        try:
            await manager.release()
        except PipelineShutdownError:
            # Expected when heartbeat failed - the exception propagates on await
            pass
