"""Integration tests for PipelineRunner lifecycle invariants.

These tests verify the order of operations in PipelineRunner.run() to ensure:
1. Lock is acquired BEFORE any data operations
2. Checkpoint load is BEFORE execute
3. Clear is BEFORE execute (for rebuild/backfill only)
4. Checkpoint delete is AFTER successful execute
5. Lock is released in finally (even on error)
"""

from collections import deque
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@dataclass
class CallRecorder:
    """Records the order of method calls for verification."""

    calls: deque = field(default_factory=deque)

    def record(self, method: str) -> None:
        """Record a method call."""
        self.calls.append(method)

    def assert_order(self, *expected: str) -> None:
        """Assert calls happened in the specified order.

        Args:
            *expected: Method names in expected order
        """
        actual = list(self.calls)
        for i, method in enumerate(expected):
            assert method in actual, f"Expected call '{method}' not found in {actual}"
            idx = actual.index(method)
            # Ensure this call comes after all previous expected calls
            for prev in expected[:i]:
                prev_idx = actual.index(prev)
                assert prev_idx < idx, (
                    f"'{prev}' (idx {prev_idx}) should come before '{method}' (idx {idx})"
                )


@pytest.fixture
def call_recorder():
    """Create a new call recorder."""
    return CallRecorder()


@pytest.fixture
def mock_services_with_recorder(call_recorder):
    """Create services that record all calls."""
    services = MagicMock()

    # Lock methods
    services.lock = AsyncMock()
    services.lock.acquire = AsyncMock(
        side_effect=lambda *a, **kw: call_recorder.record("lock.acquire")
    )
    services.lock.release = AsyncMock(
        side_effect=lambda *a, **kw: call_recorder.record("lock.release")
    )

    # Storage methods
    services.storage = MagicMock()
    services.storage.clear_silver = AsyncMock(
        side_effect=lambda *a, **kw: (call_recorder.record("storage.clear_silver"), 0)[
            1
        ]
    )
    services.storage.clear_gold = AsyncMock(
        side_effect=lambda *a, **kw: (call_recorder.record("storage.clear_gold"), 0)[1]
    )

    # Context manager support (self is passed when called as a method)
    async def services_aenter(self):
        call_recorder.record("services.__aenter__")
        return services

    async def services_aexit(self, *args):
        call_recorder.record("services.__aexit__")

    services.__aenter__ = services_aenter
    services.__aexit__ = services_aexit

    services.metrics = MagicMock()
    services.metrics.observe_histogram = MagicMock()
    services.metrics.increment_counter = MagicMock()
    return services


@pytest.fixture
def mock_checkpoint_manager_with_recorder(call_recorder):
    """Create checkpoint manager that records calls."""
    manager = AsyncMock()

    async def load_checkpoint():
        call_recorder.record("checkpoint.load")
        return None

    async def delete_checkpoint():
        call_recorder.record("checkpoint.delete")

    manager.load_checkpoint = load_checkpoint
    manager.delete_checkpoint = delete_checkpoint
    return manager


@pytest.fixture
def mock_executor_with_recorder(call_recorder):
    """Create executor that records calls."""
    executor = AsyncMock()

    async def execute(*args, **kwargs):
        call_recorder.record("executor.execute")

    executor.execute = execute
    executor.records_fetched = 100
    return executor


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.mark.integration
class TestPipelineRunnerLifecycle:
    """Tests for PipelineRunner lifecycle invariants."""

    @pytest.mark.asyncio
    async def test_rebuild_lifecycle_order(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_logger,
    ):
        """Verify call order for REBUILD run type.

        Expected order:
        1. services.__aenter__ (context manager entry)
        2. lock_manager.__aenter__ (acquire lock)
        3. storage.clear_silver
        4. storage.clear_gold
        5. checkpoint.load
        6. executor.execute
        7. checkpoint.delete
        8. lock_manager.__aexit__
        9. services.__aexit__
        """
        config = PipelineConfig(
            pipeline_name="test_lifecycle",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="test.silver",
        )
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.REBUILD,
            logger=mock_logger,
        )

        with patch("bioetl.application.core.runner.LockManager") as mock_lm:
            lock_manager = MagicMock()

            async def lm_aenter(self):
                call_recorder.record("lock_manager.__aenter__")
                return lock_manager

            async def lm_aexit(self, *args):
                call_recorder.record("lock_manager.__aexit__")

            lock_manager.__aenter__ = lm_aenter
            lock_manager.__aexit__ = lm_aexit
            mock_lm.create.return_value = lock_manager

            runner = PipelineRunner(
                config=config,
                runtime=runtime,
                services=mock_services_with_recorder,
                context=context,
                executor=mock_executor_with_recorder,
                checkpoint_manager=mock_checkpoint_manager_with_recorder,
                shutdown_signal=MagicMock(),
                logger=mock_logger,
            )

            await runner.run()

        # Verify invariants - order matters!
        call_recorder.assert_order(
            "services.__aenter__",
            "lock_manager.__aenter__",
            "storage.clear_silver",
            "storage.clear_gold",
            "checkpoint.load",
            "executor.execute",
            "checkpoint.delete",
            "lock_manager.__aexit__",
            "services.__aexit__",
        )

    @pytest.mark.asyncio
    async def test_incremental_skips_clear(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_logger,
    ):
        """Verify INCREMENTAL run does NOT clear storage.

        Medallion architecture invariant: incremental runs use merge/upsert
        and must NOT delete existing data.
        """
        config = PipelineConfig(
            pipeline_name="test_incremental",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="test.silver",
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        with patch("bioetl.application.core.runner.LockManager") as mock_lm:
            lock_manager = MagicMock()
            lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
            lock_manager.__aexit__ = AsyncMock()
            mock_lm.create.return_value = lock_manager

            runner = PipelineRunner(
                config=config,
                runtime=runtime,
                services=mock_services_with_recorder,
                context=context,
                executor=mock_executor_with_recorder,
                checkpoint_manager=mock_checkpoint_manager_with_recorder,
                shutdown_signal=MagicMock(),
                logger=mock_logger,
            )

            await runner.run()

        # Verify clear was NOT called
        calls = list(call_recorder.calls)
        assert "storage.clear_silver" not in calls
        assert "storage.clear_gold" not in calls
        # But execute was called
        assert "executor.execute" in calls

    @pytest.mark.asyncio
    async def test_lock_released_on_error(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_logger,
    ):
        """Verify lock is released even when executor raises.

        Critical invariant: lock MUST be released in finally block
        to prevent deadlocks.
        """
        config = PipelineConfig(
            pipeline_name="test_error",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="test.silver",
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Executor that raises
        failing_executor = AsyncMock()
        failing_executor.execute = AsyncMock(side_effect=RuntimeError("Test error"))
        failing_executor.records_fetched = 0

        with patch("bioetl.application.core.runner.LockManager") as mock_lm:
            lock_manager = MagicMock()

            async def lm_aenter(self):
                call_recorder.record("lock_manager.__aenter__")
                return lock_manager

            async def lm_aexit(self, *args):
                call_recorder.record("lock_manager.__aexit__")

            lock_manager.__aenter__ = lm_aenter
            lock_manager.__aexit__ = lm_aexit
            mock_lm.create.return_value = lock_manager

            runner = PipelineRunner(
                config=config,
                runtime=runtime,
                services=mock_services_with_recorder,
                context=context,
                executor=failing_executor,
                checkpoint_manager=mock_checkpoint_manager_with_recorder,
                shutdown_signal=MagicMock(),
                logger=mock_logger,
            )

            with pytest.raises(RuntimeError, match="Test error"):
                await runner.run()

        # Verify lock was released despite error
        calls = list(call_recorder.calls)
        assert "lock_manager.__aenter__" in calls
        assert "lock_manager.__aexit__" in calls
        # __aexit__ should come after __aenter__
        assert calls.index("lock_manager.__aenter__") < calls.index(
            "lock_manager.__aexit__"
        )

    @pytest.mark.asyncio
    async def test_backfill_clears_storage(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_logger,
    ):
        """Verify BACKFILL run clears storage (same as REBUILD)."""
        config = PipelineConfig(
            pipeline_name="test_backfill",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="test.silver",
        )
        runtime = RuntimeConfig(run_type=RunType.BACKFILL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.BACKFILL,
            logger=mock_logger,
        )

        with patch("bioetl.application.core.runner.LockManager") as mock_lm:
            lock_manager = MagicMock()
            lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
            lock_manager.__aexit__ = AsyncMock()
            mock_lm.create.return_value = lock_manager

            runner = PipelineRunner(
                config=config,
                runtime=runtime,
                services=mock_services_with_recorder,
                context=context,
                executor=mock_executor_with_recorder,
                checkpoint_manager=mock_checkpoint_manager_with_recorder,
                shutdown_signal=MagicMock(),
                logger=mock_logger,
            )

            await runner.run()

        # Verify clear WAS called for backfill
        calls = list(call_recorder.calls)
        assert "storage.clear_silver" in calls
        assert "storage.clear_gold" in calls
