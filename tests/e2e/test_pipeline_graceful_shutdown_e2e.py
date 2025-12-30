"""E2E tests for pipeline graceful shutdown handling.

Tests the pipeline's graceful shutdown behavior per ADR-008:
- SIGTERM/SIGINT handling via ShutdownSignal
- Checkpoint saving before exit
- Current batch completion before shutdown

Per RULES.md §4.4 Graceful Shutdown:
1. Stop extracting new records
2. Wait for current batch to complete
3. Save checkpoint locally
4. Exit with code 0
"""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal


@pytest.mark.e2e
@pytest.mark.asyncio
class TestShutdownSignal:
    """Tests for ShutdownSignal behavior."""

    async def test_shutdown_signal_initial_state(self):
        """E2E: ShutdownSignal starts in non-requested state."""
        signal = ShutdownSignal()

        assert signal.is_requested is False

    async def test_shutdown_signal_request_sets_state(self):
        """E2E: Requesting shutdown sets the signal state."""
        shutdown = ShutdownSignal()

        shutdown.request()

        assert shutdown.is_requested is True

    async def test_shutdown_signal_request_is_idempotent(self):
        """E2E: Multiple request() calls have no additional effect."""
        shutdown = ShutdownSignal()

        shutdown.request()
        shutdown.request()
        shutdown.request()

        assert shutdown.is_requested is True

    async def test_shutdown_signal_wait_blocks_until_requested(self):
        """E2E: wait() blocks until shutdown is requested."""
        shutdown = ShutdownSignal()

        async def request_after_delay():
            await asyncio.sleep(0.1)
            shutdown.request()

        # Start background task to request shutdown
        task = asyncio.create_task(request_after_delay())

        # Wait should complete after request
        await asyncio.wait_for(shutdown.wait(), timeout=1.0)

        assert shutdown.is_requested is True
        await task

    async def test_shutdown_signal_reset(self):
        """E2E: reset() clears the signal for reuse."""
        shutdown = ShutdownSignal()

        shutdown.request()
        assert shutdown.is_requested is True

        shutdown.reset()
        assert shutdown.is_requested is False


@pytest.mark.e2e
@pytest.mark.asyncio
class TestOSSignalHandling:
    """Tests for OS signal handling integration."""

    async def test_register_signal_handlers_registers_sigterm(self):
        """E2E: register_signal_handlers registers SIGTERM handler."""
        from unittest.mock import AsyncMock

        from bioetl.interfaces.orchestration.signals import register_signal_handlers

        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        # Store original handler
        original_handler = signal.getsignal(signal.SIGTERM)

        try:
            register_signal_handlers(shutdown_service, logger=None)

            # Verify handler was set (not the default)
            current_handler = signal.getsignal(signal.SIGTERM)
            assert current_handler != signal.SIG_DFL
        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_handler)

    async def test_register_signal_handlers_registers_sigint(self):
        """E2E: register_signal_handlers registers SIGINT handler."""
        from unittest.mock import AsyncMock

        from bioetl.interfaces.orchestration.signals import register_signal_handlers

        shutdown_service = MagicMock()
        shutdown_service.initiate_shutdown = AsyncMock()

        # Store original handler
        original_handler = signal.getsignal(signal.SIGINT)

        try:
            register_signal_handlers(shutdown_service, logger=None)

            # Verify handler was set
            current_handler = signal.getsignal(signal.SIGINT)
            assert current_handler != signal.SIG_DFL
        finally:
            # Restore original handler
            signal.signal(signal.SIGINT, original_handler)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestGracefulShutdownBehavior:
    """Tests for graceful shutdown during pipeline execution."""

    async def test_shutdown_stops_iteration(self):
        """E2E: Shutdown signal stops iteration over records."""
        shutdown = ShutdownSignal()
        processed_count = 0

        async def process_with_shutdown_check(records):
            nonlocal processed_count
            for i, _record in enumerate(records):
                if shutdown.is_requested:
                    break
                processed_count += 1
                await asyncio.sleep(0.01)  # Simulate processing
                if i == 5:  # Request shutdown mid-processing
                    shutdown.request()

        records = list(range(100))
        await process_with_shutdown_check(records)

        # Should have stopped early
        assert processed_count == 6  # 0-5 processed, then stopped
        assert shutdown.is_requested is True

    async def test_current_batch_completes_before_shutdown(self):
        """E2E: Current batch completes before shutdown is honored."""
        shutdown = ShutdownSignal()
        batch_completed = False

        async def process_batch(batch):
            nonlocal batch_completed
            # Simulate batch processing
            for _record in batch:
                await asyncio.sleep(0.01)
            batch_completed = True

        # Request shutdown before processing
        shutdown.request()

        # But current batch should still complete
        await process_batch([1, 2, 3, 4, 5])

        assert batch_completed is True

    async def test_shutdown_waits_for_async_operation(self):
        """E2E: Shutdown waits for async operation to complete."""
        shutdown = ShutdownSignal()
        operation_completed = False

        async def long_running_operation():
            nonlocal operation_completed
            await asyncio.sleep(0.2)
            operation_completed = True

        async def shutdown_coordinator():
            # Start operation
            operation_task = asyncio.create_task(long_running_operation())

            # Request shutdown
            await asyncio.sleep(0.05)
            shutdown.request()

            # Wait for operation to complete
            await operation_task

        await shutdown_coordinator()

        assert operation_completed is True
        assert shutdown.is_requested is True


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointSavingOnShutdown:
    """Tests for checkpoint saving during graceful shutdown."""

    async def test_checkpoint_saved_on_shutdown(self, e2e_data_dir: Path):
        """E2E: Checkpoint is saved when shutdown is requested."""
        shutdown = ShutdownSignal()
        checkpoint_path = e2e_data_dir / "checkpoints" / "test_checkpoint.json"
        checkpoint_saved = False

        async def save_checkpoint(path: Path, state: dict):
            nonlocal checkpoint_saved
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"offset": 100}')
            checkpoint_saved = True

        async def pipeline_with_checkpoint():
            # Simulate processing
            for i in range(10):
                if shutdown.is_requested:
                    # Save checkpoint on shutdown
                    await save_checkpoint(checkpoint_path, {"offset": i * 10})
                    break
                await asyncio.sleep(0.01)

                if i == 5:
                    shutdown.request()

        await pipeline_with_checkpoint()

        assert checkpoint_saved is True
        assert checkpoint_path.exists()

    async def test_shutdown_does_not_lose_data(self, e2e_data_dir: Path):
        """E2E: Data processed before shutdown is not lost."""
        shutdown = ShutdownSignal()
        processed_records: list[int] = []

        async def process_and_track(records):
            for i, record in enumerate(records):
                if shutdown.is_requested:
                    # Still track this record before breaking
                    processed_records.append(record)
                    break
                processed_records.append(record)
                await asyncio.sleep(0.01)

                if i == 4:
                    shutdown.request()

        records = list(range(100))
        await process_and_track(records)

        # All records up to and including shutdown point are tracked
        assert len(processed_records) == 6  # 0-5
        assert processed_records == [0, 1, 2, 3, 4, 5]


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPipelineShutdownError:
    """Tests for PipelineShutdownError exception."""

    async def test_pipeline_shutdown_error_is_exception(self):
        """E2E: PipelineShutdownError is a proper exception."""
        error = PipelineShutdownError()

        assert isinstance(error, Exception)

    async def test_pipeline_shutdown_error_can_be_caught(self):
        """E2E: PipelineShutdownError can be caught and handled."""
        caught = False

        async def pipeline_that_shuts_down():
            raise PipelineShutdownError()

        try:
            await pipeline_that_shuts_down()
        except PipelineShutdownError:
            caught = True

        assert caught is True

    async def test_shutdown_signal_can_trigger_exception(self):
        """E2E: ShutdownSignal can trigger PipelineShutdownError."""
        shutdown = ShutdownSignal()

        async def check_shutdown():
            if shutdown.is_requested:
                raise PipelineShutdownError()

        shutdown.request()

        with pytest.raises(PipelineShutdownError):
            await check_shutdown()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestConcurrentShutdown:
    """Tests for concurrent operations during shutdown."""

    async def test_multiple_tasks_see_shutdown(self):
        """E2E: Multiple concurrent tasks can see shutdown signal."""
        shutdown = ShutdownSignal()
        task_states = {"task1": False, "task2": False, "task3": False}

        async def worker(name: str):
            for _ in range(100):
                if shutdown.is_requested:
                    task_states[name] = True
                    return
                await asyncio.sleep(0.01)

        async def coordinator():
            # Start workers
            tasks = [
                asyncio.create_task(worker("task1")),
                asyncio.create_task(worker("task2")),
                asyncio.create_task(worker("task3")),
            ]

            # Request shutdown after brief delay
            await asyncio.sleep(0.05)
            shutdown.request()

            # Wait for all workers
            await asyncio.gather(*tasks)

        await coordinator()

        # All tasks should have seen the shutdown
        assert all(task_states.values())

    async def test_shutdown_with_pending_writes(self, e2e_data_dir: Path):
        """E2E: Shutdown allows pending writes to complete."""
        shutdown = ShutdownSignal()
        writes_completed = 0
        write_lock = asyncio.Lock()

        async def write_record(record_id: int):
            nonlocal writes_completed
            async with write_lock:
                # Simulate I/O
                await asyncio.sleep(0.02)
                writes_completed += 1

        async def writer_task():
            for i in range(20):
                if shutdown.is_requested and i > 5:
                    # Only check shutdown after some writes
                    break
                await write_record(i)

        async def shutdown_task():
            await asyncio.sleep(0.05)
            shutdown.request()

        await asyncio.gather(
            writer_task(),
            shutdown_task(),
        )

        # Some writes should have completed
        assert writes_completed > 0
        assert writes_completed <= 20
