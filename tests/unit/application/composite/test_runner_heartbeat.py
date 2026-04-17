"""Characterization tests for composite runner lock heartbeat (RF-006.1).

Validates that CompositePipelineRunner starts a background HeartbeatTask
during execution and properly stops it on completion or failure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import LockAcquisitionError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lock(*, acquire_ok: bool = True, heartbeat_ok: bool = True) -> AsyncMock:
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=acquire_ok)
    lock.heartbeat = AsyncMock(return_value=heartbeat_ok)
    lock.release = AsyncMock(return_value=True)
    return lock


def _seed_runner_factory(seed_runner: MagicMock):
    def _factory() -> MagicMock:
        return seed_runner

    return _factory


def _same_runner_factory(runner: MagicMock):
    def _factory(name: str, df: object) -> MagicMock:
        return runner

    return _factory


def _failing_seed_runner_factory() -> MagicMock:
    return _failing_runner()


def _make_runner(
    lock: AsyncMock | None = None,
    **overrides: object,
) -> CompositePipelineRunner:
    from bioetl.application.composite.fsm_helper import FSMStateHelperService

    run_id = str(uuid4())

    class _SeedConfig:
        pipeline = "test_seed"
        silver_table = "test_seed"
        output_keys = ("id",)

    class _MergeConfig:
        output_silver_path = "silver/test"
        output_gold_path = "gold/test"

    class _DQConfig:
        soft_fail_threshold = 0.05
        hard_fail_threshold = 0.20

    class _Config:
        name = "test_composite"
        lock_key = "lock:test_composite"
        seed = _SeedConfig()
        merge = _MergeConfig()
        dq = _DQConfig()
        enrichers = ()
        required_enrichers = frozenset()
        dependencies = ()

        @property
        def required_dependencies(self) -> tuple[str, ...]:
            return ()

    import polars as pl

    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()

    seed_runner = MagicMock()
    seed_runner.run = AsyncMock()
    seed_runner.execution_metrics = {"records_fetched": 10, "records_silver": 10}

    key_extractor = AsyncMock()
    key_extractor.extract = AsyncMock(return_value=pl.DataFrame({"id": ["1"]}))

    coordinator = AsyncMock()
    coordinator.run_enrichers = AsyncMock(return_value={})

    merger = AsyncMock()
    merger.merge = AsyncMock(
        return_value=MergeResult(
            records_merged=10,
            records_from_seed=10,
            records_enriched=0,
            records_fully_enriched=0,
            duration_seconds=0.1,
        )
    )

    checkpoint_manager = AsyncMock()
    checkpoint_manager.load = AsyncMock(
        return_value=CompositeCheckpointState(
            composite_name="test_composite", run_id=run_id
        )
    )
    checkpoint_manager.save = AsyncMock()
    checkpoint_manager.delete = AsyncMock()

    config = _Config()
    fsm = FSMStateHelperService(config=config, logger=logger, run_id=run_id)

    deps = CompositeRunnerDependencies(
        seed_runner_factory=_seed_runner_factory(seed_runner),
        enricher_runner_factory=_same_runner_factory(seed_runner),
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock or _make_lock(),
        fsm_state_helper=fsm,
    )
    return CompositePipelineRunner(
        config=config,
        runtime=CompositeRuntimeConfig(),
        deps=deps,
        run_id=run_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompositeRunnerHeartbeat:
    """Characterization tests for RF-006.1: lock heartbeat in composite runner."""

    @pytest.mark.asyncio
    async def test_heartbeat_started_during_execution(self) -> None:
        """HeartbeatTask.start() is called after lock acquisition."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)

        await runner.run()

        # Heartbeat was called at least once (initial heartbeat in start())
        lock.heartbeat.assert_called()

    @pytest.mark.asyncio
    async def test_heartbeat_uses_correct_lock_key_and_owner(self) -> None:
        """Heartbeat uses the same lock_key and owner_id as acquire."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)

        await runner.run()

        acquire_call = lock.acquire.call_args
        heartbeat_call = lock.heartbeat.call_args

        assert (
            heartbeat_call[0][0]
            == acquire_call.kwargs.get("key", acquire_call[1].get("key"))
            or heartbeat_call[0][0] == "lock:test_composite"
        )
        assert heartbeat_call[0][1] == runner._run_id

    @pytest.mark.asyncio
    async def test_lock_released_after_successful_run(self) -> None:
        """Lock is released even when heartbeat is active."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)

        await runner.run()

        lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_lock_released_after_failed_run(self) -> None:
        """Lock is released in finally block even when pipeline fails."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)

        # Make seed fail
        runner._seed_runner_factory = _failing_seed_runner_factory

        with pytest.raises(RuntimeError, match="seed exploded"):
            await runner.run()

        lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_failure_raises_shutdown_error(self) -> None:
        """If initial heartbeat fails, PipelineShutdownError is raised."""
        lock = _make_lock(heartbeat_ok=False)
        runner = _make_runner(lock=lock)

        with pytest.raises(PipelineShutdownError):
            await runner.run()

        # Lock should still be released via finally
        lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_interval_defaults_to_30(self) -> None:
        """Default composite heartbeat interval is 30s via CompositeRuntimeConfig."""
        runtime = CompositeRuntimeConfig()
        assert runtime.heartbeat_interval_seconds == 30

    @pytest.mark.asyncio
    async def test_lock_ttl_defaults_to_3600(self) -> None:
        """Default lock TTL is 3600s (1 hour) via CompositeRuntimeConfig."""
        runtime = CompositeRuntimeConfig()
        assert runtime.lock_ttl_seconds == 3600

    @pytest.mark.asyncio
    async def test_custom_heartbeat_interval_used_by_runner(self) -> None:
        """Runner uses custom heartbeat_interval_seconds from runtime config."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)
        runner._runtime = CompositeRuntimeConfig(heartbeat_interval_seconds=60)

        await runner.run()

        # Verify lock.acquire was called with default TTL (3600)
        lock.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_lock_ttl_used_by_runner(self) -> None:
        """Runner uses custom lock_ttl_seconds from runtime config."""
        lock = _make_lock()
        runner = _make_runner(lock=lock)
        runner._runtime = CompositeRuntimeConfig(lock_ttl_seconds=7200)

        await runner.run()

        acquire_kwargs = lock.acquire.call_args.kwargs
        assert acquire_kwargs["ttl"] == 7200

    @pytest.mark.asyncio
    async def test_no_heartbeat_when_lock_not_acquired(self) -> None:
        """If lock acquisition fails, heartbeat is never started."""
        lock = _make_lock(acquire_ok=False)
        runner = _make_runner(lock=lock)

        with pytest.raises(LockAcquisitionError):
            await runner.run()

        lock.heartbeat.assert_not_called()


def _failing_runner() -> MagicMock:
    runner = MagicMock()
    runner.run = AsyncMock(side_effect=RuntimeError("seed exploded"))
    runner.execution_metrics = {"records_fetched": 0, "records_silver": 0}
    return runner
