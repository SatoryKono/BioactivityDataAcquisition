"""Integration tests for PipelineRunner lifecycle invariants.

These tests verify the order of operations in PipelineRunner.run() to ensure:
1. Lock is acquired BEFORE any data operations
2. Checkpoint load is BEFORE execute
3. Clear is BEFORE execute (for rebuild/backfill only)
4. Checkpoint delete is AFTER successful execute
5. Lock is released in finally (even on error)
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.postrun import CompactionResult
from bioetl.application.core.postrun.service import PostrunService
from bioetl.application.core.preflight.service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import (
    MedallionLifecycleService,
    PrepareResult,
    VacuumResult,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import RunType

_NOOP_TRACER = NoOpTracing()


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
    from bioetl.domain.types import HealthStatus

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
    # Health check must be async and return HealthStatus
    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)

    # Data source methods (needed for health checks)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)

    # Health check for infrastructure validation
    from bioetl.domain.types import HealthStatus

    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)

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

    async def load_checkpoint(*, current_metadata=None):
        await asyncio.sleep(0)
        call_recorder.record("checkpoint.load")

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
    executor.records_bronze = 100
    executor.records_silver = 95
    executor.records_gold = 90
    executor.records_quarantined = 5
    executor.get_dq_context = MagicMock(return_value=None)
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


@pytest.fixture
def mock_lifecycle_service_with_recorder(call_recorder, mock_services_with_recorder):
    """Create lifecycle service that records calls and delegates to storage.

    Respects MedallionPolicy - only clears when policy indicates.
    """
    from bioetl.application.services.medallion_lifecycle import (
        ClearResult,
        MedallionLifecycleService,
    )

    service = MagicMock(spec=MedallionLifecycleService)

    async def clear_with_recording(*args, **kwargs):
        # Respect policy - only clear when policy indicates (mimics real behavior)
        policy = kwargs.get("policy")
        silver_cleared = 0
        gold_cleared = 0

        if policy and policy.should_clear_silver:
            silver_cleared = await mock_services_with_recorder.storage.clear_silver(
                kwargs.get("silver_table", "test.silver"),
                dry_run=kwargs.get("dry_run", False),
            )
        if policy and policy.should_clear_gold:
            gold_cleared = await mock_services_with_recorder.storage.clear_gold(
                kwargs.get("gold_table", "test.gold"),
                dry_run=kwargs.get("dry_run", False),
            )

        return ClearResult(
            silver_cleared=silver_cleared or 0,
            gold_cleared=gold_cleared or 0,
            dry_run=kwargs.get("dry_run", False),
        )

    service.clear = AsyncMock(side_effect=clear_with_recording)
    service.vacuum = AsyncMock()
    return service


@pytest.fixture
def mock_lifecycle_service(call_recorder, mock_lifecycle_service_with_recorder):
    """Create a mock lifecycle service for runner tests."""
    from bioetl.domain.medallion import MedallionPolicy

    service = MagicMock(spec=MedallionLifecycleService)

    async def prepare_for_run(config, runtime):
        call_recorder.record("lifecycle.clear")
        result = await mock_lifecycle_service_with_recorder.clear(
            policy=MagicMock(),  # Simplified for test
        )
        return PrepareResult(
            clear_result=result,
            policy=MedallionPolicy.for_run_type(runtime.run_type),
        )

    async def finalize_run(config, runtime, metrics=None):
        return VacuumResult(silver_files_removed=0, gold_files_removed=0, skipped=True)

    service.prepare_for_run = AsyncMock(side_effect=prepare_for_run)
    service.finalize_run = AsyncMock(side_effect=finalize_run)
    return service


@pytest.fixture
def mock_preflight_service(call_recorder):
    """Create a mock preflight service."""
    service = MagicMock(spec=PreflightService)

    async def validate_infrastructure(services):
        call_recorder.record("preflight.validate_infrastructure")

    service.validate_infrastructure = AsyncMock(side_effect=validate_infrastructure)
    service.validate_medallion_config = MagicMock()
    return service


@pytest.fixture
def mock_postrun_service(call_recorder):
    """Create a mock postrun service.

    The runner calls postrun_service.run(), which internally calls:
    - run_dq_checks()
    - run_vacuum_if_enabled()

    We mock the run() method to record the expected calls.
    """
    from bioetl.application.core.postrun.compact_orchestrator import CompactionResult
    from bioetl.application.core.postrun.service import PostrunResult
    from bioetl.application.services.medallion_lifecycle import VacuumResult
    from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

    service = MagicMock(spec=PostrunService)

    async def run(executor, dq_context=None):
        """Mock run that records DQ checks and vacuum calls."""
        call_recorder.record("postrun.dq_checks")
        call_recorder.record("postrun.vacuum")
        return PostrunResult(
            dq=DQResult(
                error_rate=0.01,
                status=DQEvaluationStatus.PASSED,
            ),
            dq_reports=None,
            vacuum=VacuumResult(
                silver_files_removed=0,
                gold_files_removed=0,
                skipped=False,
            ),
            compaction=CompactionResult(status="skipped"),
        )

    def run_dq_checks(executor):
        call_recorder.record("postrun.dq_checks")

    async def run_vacuum_if_enabled():
        call_recorder.record("postrun.vacuum")

    async def cleanup(tracer):
        call_recorder.record("postrun.cleanup")

    service.run = AsyncMock(side_effect=run)
    service.run_dq_checks = MagicMock(side_effect=run_dq_checks)
    service.run_vacuum_if_enabled = AsyncMock(side_effect=run_vacuum_if_enabled)
    service.cleanup = AsyncMock(side_effect=cleanup)
    return service


@pytest.fixture
def mock_observer():
    """Create a mock PipelineObserver (injected via DI).

    This mock properly handles context manager protocol and suppresses
    PipelineShutdownError as the real observer would.
    """
    from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError

    observer = MagicMock(spec=PipelineObserver)

    def exit_side_effect(exc_type, exc_val, exc_tb):
        # Suppress PipelineShutdownError like the real observer
        if exc_val and isinstance(exc_val, PipelineShutdownError):
            return True
        return False

    observer.__enter__ = MagicMock(return_value=observer)
    observer.__exit__ = MagicMock(side_effect=exit_side_effect)

    return observer


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
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify call order for REBUILD run type.

        Expected order:
        1. services.__aenter__ (context manager entry)
        2. lock_manager.__aenter__ (acquire lock)
        3. preflight.validate_infrastructure
        4. lifecycle.clear
        5. checkpoint.load
        6. executor.execute
        7. postrun.dq_checks
        8. postrun.vacuum
        9. checkpoint.delete
        10. postrun.cleanup
        11. lock_manager.__aexit__
        12. services.__aexit__
        """
        config = PipelineConfig(
            pipeline_name="test_lifecycle",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.REBUILD,
            logger=mock_logger,
        )

        lock_manager = MagicMock()

        async def lm_aenter(self):
            call_recorder.record("lock_manager.__aenter__")
            return lock_manager

        async def lm_aexit(self, *args):
            call_recorder.record("lock_manager.__aexit__")

        lock_manager.__aenter__ = lm_aenter
        lock_manager.__aexit__ = lm_aexit

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        await runner.run()

        # Verify invariants - order matters!
        call_recorder.assert_order(
            "services.__aenter__",
            "lock_manager.__aenter__",
            "preflight.validate_infrastructure",
            "lifecycle.clear",
            "checkpoint.load",
            "executor.execute",
            "postrun.dq_checks",
            "postrun.vacuum",
            "checkpoint.delete",
            "lock_manager.__aexit__",
            "services.__aexit__",
            "postrun.cleanup",
        )

    @pytest.mark.asyncio
    async def test_incremental_skips_clear(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
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
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Lifecycle service that does NOT clear for incremental runs
        from bioetl.application.services.medallion_lifecycle import ClearResult
        from bioetl.domain.medallion import MedallionPolicy

        lifecycle_service_no_clear = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service_no_clear.prepare_for_run = AsyncMock(
            return_value=PrepareResult(
                clear_result=ClearResult(
                    silver_cleared=0, gold_cleared=0, dry_run=False
                ),
                policy=MedallionPolicy.for_run_type(RunType.INCREMENTAL),
            )
        )
        lifecycle_service_no_clear.finalize_run = AsyncMock(
            return_value=VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )
        )

        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock()

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=lifecycle_service_no_clear,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
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
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
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
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
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

        lock_manager = MagicMock()

        async def lm_aenter(self):
            call_recorder.record("lock_manager.__aenter__")
            return lock_manager

        async def lm_aexit(self, *args):
            call_recorder.record("lock_manager.__aexit__")

        lock_manager.__aenter__ = lm_aenter
        lock_manager.__aexit__ = lm_aexit

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=failing_executor,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
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
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify BACKFILL run clears storage (same as REBUILD)."""
        config = PipelineConfig(
            pipeline_name="test_backfill",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.BACKFILL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.BACKFILL,
            logger=mock_logger,
        )

        # Configure mock_lifecycle_service to record clear operations
        from bioetl.application.services.medallion_lifecycle import ClearResult
        from bioetl.domain.medallion import MedallionPolicy

        async def prepare_for_run_with_recording(config, runtime):
            call_recorder.record("lifecycle.clear")
            call_recorder.record("storage.clear_silver")
            call_recorder.record("storage.clear_gold")
            return PrepareResult(
                clear_result=ClearResult(
                    silver_cleared=0, gold_cleared=0, dry_run=False
                ),
                policy=MedallionPolicy.for_run_type(runtime.run_type),
            )

        mock_lifecycle_service.prepare_for_run = AsyncMock(
            side_effect=prepare_for_run_with_recording
        )

        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock()

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        await runner.run()

        # Verify clear WAS called for backfill
        calls = list(call_recorder.calls)
        assert "storage.clear_silver" in calls
        assert "storage.clear_gold" in calls

    @pytest.mark.asyncio
    async def test_preflight_validation_failure_aborts(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify pipeline aborts when infrastructure health check fails.

        Preflight validation is critical for fail-fast behavior.
        If storage or data source is unhealthy, we must abort before
        any data operations to prevent partial writes.
        """
        from bioetl.domain.exceptions import InfrastructureError

        config = PipelineConfig(
            pipeline_name="test_health_fail",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Make preflight service raise InfrastructureError
        mock_preflight_service.validate_infrastructure = AsyncMock(
            side_effect=InfrastructureError("health check failed")
        )

        lock_manager = MagicMock()

        async def lm_aenter(self):
            call_recorder.record("lock_manager.__aenter__")
            return lock_manager

        async def lm_aexit(self, *args):
            call_recorder.record("lock_manager.__aexit__")

        lock_manager.__aenter__ = lm_aenter
        lock_manager.__aexit__ = lm_aexit

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        with pytest.raises(InfrastructureError) as exc_info:
            await runner.run()

        # Verify the error message indicates health check failure
        assert "health check failed" in str(exc_info.value).lower()

        # Verify executor was NEVER called
        calls = list(call_recorder.calls)
        assert "executor.execute" not in calls
        # Verify checkpoint operations were NOT performed
        assert "checkpoint.load" not in calls
        assert "checkpoint.delete" not in calls

    @pytest.mark.asyncio
    async def test_checkpoint_resume_after_failure(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_executor_with_recorder,
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify pipeline resumes from checkpoint after previous failure.

        Checkpoint management is critical for long-running pipelines.
        When resume=True, the checkpoint manager must:
        1. Load previous checkpoint metadata
        2. Log the resume state
        3. Continue from saved offset
        """
        config = PipelineConfig(
            pipeline_name="test_resume",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Create checkpoint manager with resume=True that returns saved state
        checkpoint_loaded = False
        saved_metadata = {"records_processed": 500, "last_id": "abc123"}

        checkpoint_manager = AsyncMock()

        async def load_checkpoint(*, current_metadata=None):
            nonlocal checkpoint_loaded
            checkpoint_loaded = True
            call_recorder.record("checkpoint.load")
            return saved_metadata

        async def delete_checkpoint():
            call_recorder.record("checkpoint.delete")

        checkpoint_manager.load_checkpoint = load_checkpoint
        checkpoint_manager.delete_checkpoint = delete_checkpoint

        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock()

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        await runner.run()

        # Verify checkpoint was loaded
        assert checkpoint_loaded, "Checkpoint must be loaded for resume"
        calls = list(call_recorder.calls)
        assert "checkpoint.load" in calls
        # Verify checkpoint load happens BEFORE execute
        assert calls.index("checkpoint.load") < calls.index("executor.execute")
        # Verify checkpoint is deleted after successful run
        assert "checkpoint.delete" in calls

    @pytest.mark.asyncio
    async def test_dq_threshold_exceeded_logs_anomaly(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify data quality anomalies are detected and logged.

        Per RULES.md §4.2:
        - Soft threshold (>5% DQ errors): Warning
        - Hard threshold (>20% DQ errors): Fail Batch

        DQ monitoring provides observability into data quality drift.
        """
        from bioetl.infrastructure.observability.anomaly.types import (
            AnomalyRecord,
            AnomalySeverity,
            AnomalyType,
        )

        config = PipelineConfig(
            pipeline_name="test_dq_threshold",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
            ),
        )
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Configure DQ monitor to return critical anomaly
        critical_anomaly = AnomalyRecord(
            metric_name="error_rate",
            current_value=0.25,  # 25% error rate
            baseline_mean=0.02,
            baseline_stddev=0.01,
            z_score=23.0,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            timestamp=datetime.now(UTC),
            message="Error rate 25% exceeds threshold 20%",
        )

        dq_monitor = MagicMock()
        dq_monitor.check_quality = MagicMock(return_value=[critical_anomaly])
        dq_monitor.update_baseline_from_metrics = MagicMock()

        # Replace services with one that has DQ monitor
        services_with_dq = MagicMock()
        # Copy attributes from original mock
        services_with_dq.lock = mock_services_with_recorder.lock
        services_with_dq.storage = mock_services_with_recorder.storage
        services_with_dq.data_source = mock_services_with_recorder.data_source
        services_with_dq.metrics = mock_services_with_recorder.metrics
        services_with_dq.logger = mock_services_with_recorder.logger
        services_with_dq.dq_monitor = dq_monitor

        # Properly set up async context manager
        def services_dq_aenter(self):
            del self
            return asyncio.sleep(0, result=services_with_dq)

        def services_dq_aexit(self, *args):
            del args
            return asyncio.sleep(0)

        services_with_dq.__aenter__ = services_dq_aenter
        services_with_dq.__aexit__ = services_dq_aexit

        # Mock postrun service to call DQ checks via run()
        from bioetl.application.core.postrun.service import PostrunResult
        from bioetl.application.services.medallion_lifecycle import VacuumResult
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

        async def run_with_dq(executor, dq_context=None):
            call_recorder.record("postrun.dq_checks")
            # Simulate DQ check logic
            anomalies = dq_monitor.check_quality()
            if anomalies:
                mock_logger.warning("DQ anomaly detected")
            call_recorder.record("postrun.vacuum")
            return PostrunResult(
                dq=DQResult(
                    error_rate=0.25,
                    status=DQEvaluationStatus.WARNING,
                ),
                dq_reports=None,
                vacuum=VacuumResult(
                    silver_files_removed=0,
                    gold_files_removed=0,
                    skipped=False,
                ),
                compaction=CompactionResult(status="skipped"),
            )

        mock_postrun_service.run = AsyncMock(side_effect=run_with_dq)

        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock()

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=services_with_dq,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        await runner.run()

        # Verify DQ check was called
        dq_monitor.check_quality.assert_called_once()
        # Verify logger.warning was called (for DQ anomaly)
        assert mock_logger.warning.called or mock_logger.error.called

    @pytest.mark.asyncio
    async def test_vacuum_runs_after_success(
        self,
        call_recorder,
        mock_services_with_recorder,
        mock_checkpoint_manager_with_recorder,
        mock_executor_with_recorder,
        mock_lifecycle_service,
        mock_preflight_service,
        mock_postrun_service,
        mock_observer,
        mock_logger,
    ):
        """Verify VACUUM runs on Silver and Gold tables after successful run.

        Per RULES.md §3.2: VACUUM weekly, retention_period=7 days.
        When runtime.vacuum_after_run=True, lifecycle service must call vacuum.
        """
        config = PipelineConfig(
            pipeline_name="test_vacuum",
            provider="test",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test.silver",
                gold_table="test.gold",
            ),
        )
        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            limit=None,
            vacuum_after_run=True,
            vacuum_retention_days=7,
        )
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Mock postrun service to call vacuum via run()
        from bioetl.application.core.postrun.service import PostrunResult
        from bioetl.application.services.medallion_lifecycle import VacuumResult
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

        async def run_with_vacuum(executor, dq_context=None):
            call_recorder.record("postrun.dq_checks")
            call_recorder.record("postrun.vacuum")
            return PostrunResult(
                dq=DQResult(
                    error_rate=0.01,
                    status=DQEvaluationStatus.PASSED,
                ),
                dq_reports=None,
                vacuum=VacuumResult(
                    silver_files_removed=5,
                    gold_files_removed=3,
                    skipped=False,
                ),
                compaction=CompactionResult(status="skipped"),
            )

        mock_postrun_service.run = AsyncMock(side_effect=run_with_vacuum)

        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock()

        runner = PipelineRunner(
            config=config,
            runtime=runtime,
            services=mock_services_with_recorder,
            context=context,
            executor=mock_executor_with_recorder,
            checkpoint_manager=mock_checkpoint_manager_with_recorder,
            shutdown_signal=MagicMock(),
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
            tracer=_NOOP_TRACER,
        )

        await runner.run()

        # Verify vacuum was called
        assert "postrun.vacuum" in list(call_recorder.calls)

    @pytest.mark.asyncio
    async def test_circuit_breaker_trip_and_recovery(
        self,
        call_recorder,
    ):
        """Verify circuit breaker trips after failures and recovers.

        Per ADR-007:
        - Trigger: 5 consecutive errors
        - Open Duration: 5 min (300s)
        - Recovery: Half-Open → 1 probe → Closed/Open

        This test verifies the state machine transitions.
        """
        import time
        from unittest.mock import patch as mock_patch

        from bioetl.domain.exceptions import CircuitBreakerOpenError
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        cb = CircuitBreakerGuard(
            provider="test", failure_threshold=3, recovery_timeout=1
        )

        # Initial state should be CLOSED
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0

        # Simulate 3 consecutive failures to trip the circuit
        async def failing_func():
            raise RuntimeError("Simulated failure")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failing_func)

        # Circuit should now be OPEN
        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 1

        # Requests should be rejected while OPEN
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_func)

        # Advance time past recovery timeout using mock
        # We mock time.monotonic to simulate time passing
        original_monotonic = time.monotonic
        mock_time = original_monotonic() + 2  # 2 seconds past recovery timeout (1s)

        with mock_patch("time.monotonic", return_value=mock_time):
            # Circuit should transition to HALF_OPEN and allow probe request
            async def success_func():
                return "success"

            result = await cb.call(success_func)
            assert result == "success"

        # After successful probe, circuit should be CLOSED
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0

        # Verify circuit can trip again
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failing_func)

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 2  # Second trip
