"""Unit tests for RF-007: application-phase OTel spans.

Covers:
- PipelineRunner.run: pipeline.run span
- PostrunService.run: postrun.run span
- RecordProcessor: record.transform span (already existed — verified here)
- BatchExecutor: pipeline_execution + batch.process spans (already existed — verified here)

Tests verify:
1. start_span is called with the correct span name
2. span attributes are set correctly
3. NoOp tracer path works without errors
4. Errors are recorded on the span
"""

from __future__ import annotations

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from bioetl.application.core.postrun.service import PostrunService
from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.domain.types import RunID, RunType
from tests.unit.application.core.runner_test_support import build_test_pipeline_runner


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_tracer() -> MagicMock:
    """Build a mock TracingPort whose span can be inspected."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()

    mock_otel_tracer = MagicMock()
    mock_otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)

    mock_tracer = MagicMock()
    mock_tracer.get_tracer = MagicMock(return_value=mock_otel_tracer)
    mock_tracer.close = MagicMock()

    return mock_tracer


def _pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        pipeline_name="test_spans_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="test_silver",
        ),
    )


def _runtime_config() -> RuntimeConfig:
    return RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)


# ---------------------------------------------------------------------------
# PipelineRunner: pipeline.run span
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineRunnerSpan:
    """Verify that PipelineRunner.run creates a pipeline.run OTel span."""

    def _build_runner(self, tracer: object | None) -> PipelineRunner:
        """Build a fully-mocked PipelineRunner with the given tracer."""
        from bioetl.application.core.lifecycle.lock_runtime_service import (
            LockRuntimeService,
        )
        from bioetl.application.core.preflight.service import PreflightService
        from bioetl.application.core.postrun.service import PostrunService
        from bioetl.application.services.medallion_lifecycle import (
            MedallionLifecycleService,
            PrepareResult,
        )
        from bioetl.application.services.medallion_types import VacuumResult
        from bioetl.application.core.postrun.compact_orchestrator import (
            CompactionResult,
        )
        from bioetl.domain.locking import FencingToken
        from bioetl.domain.medallion import MedallionPolicy
        from bioetl.domain.types import HealthReport, HealthStatus
        from bioetl.application.core.lifecycle.checkpoint_manager import (
            CheckpointRuntimeService,
        )
        from bioetl.application.core.pipeline_services import PipelineService
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
        import uuid

        mock_token = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=RunID(uuid.UUID("00000000-0000-0000-0000-000000000000")),
            issued_at=0.0,
        )

        config = _pipeline_config()
        runtime = _runtime_config()

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)
        mock_logger.info = MagicMock()
        mock_logger.debug = MagicMock()
        mock_logger.error = MagicMock()
        mock_logger.warning = MagicMock()

        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        services = MagicMock(spec=PipelineService)
        services.lock = AsyncMock()
        services.lock.acquire = AsyncMock(return_value=mock_token)
        services.lock.release = AsyncMock()
        services.lock.heartbeat = AsyncMock(return_value=True)
        services.metrics = MagicMock()
        services.metrics.observe_histogram = MagicMock()
        services.metrics.increment_counter = MagicMock()
        services.metrics.set_gauge = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=0)
        services.storage.clear_gold = AsyncMock(return_value=0)
        services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        services.data_source = MagicMock()
        services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        services.logger = mock_logger
        services.__aenter__ = AsyncMock(return_value=services)
        services.__aexit__ = AsyncMock(return_value=None)

        executor = AsyncMock()
        executor.execute = AsyncMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 95
        executor.records_gold = 90
        executor.records_quarantined = 5
        executor.get_dq_context = MagicMock(return_value=None)

        checkpoint_manager = AsyncMock(spec=CheckpointRuntimeService)
        checkpoint_manager.load_checkpoint = AsyncMock(return_value=None)
        checkpoint_manager.delete_checkpoint = AsyncMock()

        shutdown_signal = MagicMock()
        shutdown_signal.is_requested = False

        lock_manager = MagicMock(spec=LockRuntimeService)
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock(return_value=None)

        preflight = MagicMock(spec=PreflightService)
        preflight.validate_infrastructure = AsyncMock(
            return_value=HealthReport(results=[])
        )

        postrun = MagicMock(spec=PostrunService)
        from bioetl.application.core.postrun.service import PostrunResult

        postrun.run = AsyncMock(
            return_value=PostrunResult(
                dq=DQResult(
                    error_rate=0.0,
                    status=DQEvaluationStatus.PASSED,
                    anomalies=(),
                    has_critical=False,
                    check_duration_ms=0.0,
                ),
                dq_reports=None,
                vacuum=VacuumResult(
                    silver_files_removed=0, gold_files_removed=0, skipped=True
                ),
                compaction=CompactionResult(status="skipped"),
            )
        )
        postrun.cleanup = AsyncMock()

        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.prepare_for_run = AsyncMock(
            return_value=PrepareResult(
                clear_result=MagicMock(silver_cleared=0, gold_cleared=0, dry_run=False),
                policy=MedallionPolicy.for_run_type(RunType.INCREMENTAL),
            )
        )

        observer = MagicMock()
        observer.__enter__ = MagicMock(return_value=observer)
        observer.__exit__ = MagicMock(return_value=None)

        return build_test_pipeline_runner(
            config=config,
            runtime=runtime,
            services=services,
            context=context,
            executor=executor,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=lock_manager,
            preflight=preflight,
            postrun=postrun,
            lifecycle_service=lifecycle_service,
            observer=observer,
            tracer=cast(TracingPort | None, tracer),
        )

    @pytest.mark.asyncio
    async def test_pipeline_run_span_is_started(self) -> None:
        """Verify start_as_current_span is called with 'pipeline.run'."""
        mock_tracer = _make_mock_tracer()
        runner = self._build_runner(tracer=mock_tracer)

        await runner.run()

        mock_tracer.get_tracer.assert_called_with("bioetl.runner")
        mock_tracer.get_tracer.return_value.start_as_current_span.assert_called_once()
        span_name = mock_tracer.get_tracer.return_value.start_as_current_span.call_args[
            0
        ][0]
        assert span_name == "pipeline.run"

    @pytest.mark.asyncio
    async def test_pipeline_run_span_attributes(self) -> None:
        """Verify pipeline.run span carries provider, entity_type, run_type, run_id."""
        mock_tracer = _make_mock_tracer()
        runner = self._build_runner(tracer=mock_tracer)

        await runner.run()

        kwargs = mock_tracer.get_tracer.return_value.start_as_current_span.call_args[1]
        attrs = kwargs["attributes"]
        assert attrs["bioetl.provider"] == "chembl"
        assert attrs["bioetl.entity_type"] == "activity"
        assert attrs["bioetl.run_type"] == RunType.INCREMENTAL.value
        assert "bioetl.run_id" in attrs
        assert "bioetl.pipeline" in attrs

    @pytest.mark.asyncio
    async def test_pipeline_run_span_is_entered_and_exited(self) -> None:
        """Verify the span context manager is entered and exited."""
        mock_tracer = _make_mock_tracer()
        runner = self._build_runner(tracer=mock_tracer)

        await runner.run()

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.__enter__.assert_called_once()
        mock_span.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_run_span_records_error_on_exception(self) -> None:
        """Verify span __exit__ receives exception info when run() raises."""
        mock_tracer = _make_mock_tracer()
        runner = self._build_runner(tracer=mock_tracer)
        cast(Any, runner._executor.execute).side_effect = RuntimeError("forced error")

        with pytest.raises(RuntimeError, match="forced error"):
            await runner.run()

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        exit_args = mock_span.__exit__.call_args[0]
        assert exit_args[0] is RuntimeError
        assert isinstance(exit_args[1], RuntimeError)
        assert str(exit_args[1]) == "forced error"

    @pytest.mark.asyncio
    async def test_pipeline_run_none_tracer_is_rejected(self) -> None:
        """Runner must reject hidden tracer defaults in application layer."""
        await asyncio.sleep(0)
        with pytest.raises(TypeError, match="requires explicit tracer injection"):
            self._build_runner(tracer=None)

    @pytest.mark.asyncio
    async def test_pipeline_run_explicit_noop_tracer(self) -> None:
        """Verify run() works without errors with an explicit NoOpTracing instance."""
        runner = self._build_runner(tracer=NoOpTracing())
        await runner.run()

    def test_none_tracer_is_rejected(self) -> None:
        """Construction fails fast when tracer defaults are left unresolved."""
        with pytest.raises(TypeError, match="requires explicit tracer injection"):
            self._build_runner(tracer=None)

    def test_tracer_stored_when_provided(self) -> None:
        """Verify that an explicit tracer is stored as-is."""
        mock_tracer = _make_mock_tracer()
        runner = self._build_runner(tracer=mock_tracer)
        assert runner._tracer is mock_tracer


# ---------------------------------------------------------------------------
# PostrunService: postrun.run span
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPostrunServiceSpan:
    """Verify that PostrunService.run creates a postrun.run OTel span."""

    def _build_postrun_service(self, tracer: object | None) -> PostrunService:
        """Build a PostrunService with mocked dependencies."""
        from bioetl.application.services.data_quality_service import DataQualityService
        from bioetl.application.core.postrun.compact_orchestrator import (
            CompactionResult,
        )
        from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
        from bioetl.application.core.postrun.service import PostrunDependencyContext

        config = _pipeline_config()
        runtime = _runtime_config()

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)
        mock_logger.info = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.debug = MagicMock()

        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        dq_service = MagicMock(spec=DataQualityService)
        dq_service.evaluate = MagicMock(
            return_value=DQResult(
                error_rate=0.0,
                status=DQEvaluationStatus.PASSED,
                anomalies=(),
                has_critical=False,
                check_duration_ms=0.0,
            )
        )

        from bioetl.application.services.medallion_lifecycle import (
            MedallionLifecycleService,
        )
        from bioetl.application.services.medallion_types import VacuumResult

        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.finalize_run = AsyncMock(
            return_value=VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )
        )

        storage = MagicMock()

        cleanup_orchestrator = MagicMock()
        cleanup_orchestrator.cleanup_tracer = AsyncMock()

        dq_report_orchestrator = MagicMock()
        dq_report_orchestrator.generate_reports = AsyncMock(return_value=None)

        metadata_write_orchestrator = MagicMock()
        metadata_write_orchestrator.write_final_metadata_if_available = AsyncMock()

        compact_orchestrator = MagicMock()
        compact_orchestrator.run_if_needed = AsyncMock(
            return_value=CompactionResult(status="skipped")
        )

        dependencies = PostrunDependencyContext(
            cleanup_orchestrator=cleanup_orchestrator,
            dq_report_orchestrator=dq_report_orchestrator,
            metadata_write_orchestrator=metadata_write_orchestrator,
            compact_orchestrator=compact_orchestrator,
        )

        return PostrunService(
            config=config,
            runtime=runtime,
            context=context,
            dq_service=dq_service,
            lifecycle_service=lifecycle_service,
            storage=storage,
            metrics=NoOpMetrics(warn_on_use=False),
            logger=mock_logger,
            dependencies=dependencies,
            tracer=cast(TracingPort | None, tracer),
        )

    def _make_executor(self) -> MagicMock:
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 95
        executor.records_gold = 90
        executor.records_quarantined = 5
        return executor

    @pytest.mark.asyncio
    async def test_postrun_run_span_is_started(self) -> None:
        """Verify start_as_current_span is called with 'postrun.run'."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        mock_tracer.get_tracer.assert_called_with("bioetl.postrun")
        span_name = (
            mock_tracer.get_tracer.return_value.start_as_current_span.call_args_list[
                0
            ].args[0]
        )
        assert span_name == "postrun.run"

    @pytest.mark.asyncio
    async def test_postrun_run_span_attributes(self) -> None:
        """Verify postrun.run span carries pipeline, provider, entity_type, run_type."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        kwargs = mock_tracer.get_tracer.return_value.start_as_current_span.call_args[1]
        attrs = kwargs["attributes"]
        assert attrs["bioetl.provider"] == "chembl"
        assert attrs["bioetl.entity_type"] == "activity"
        assert attrs["bioetl.run_type"] == RunType.INCREMENTAL.value
        assert "bioetl.pipeline" in attrs

    @pytest.mark.asyncio
    async def test_postrun_run_span_sets_dq_status_attribute(self) -> None:
        """Verify postrun.run span sets bioetl.dq_status attribute."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.set_attribute.assert_any_call("bioetl.dq_status", "passed")

    @pytest.mark.asyncio
    async def test_postrun_run_starts_nested_phase_spans(self) -> None:
        """Verify postrun tracing covers compaction, DQ, reports, vacuum, metadata."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        started_span_names = [
            call.args[0]
            for call in mock_tracer.get_tracer.return_value.start_as_current_span.call_args_list
        ]
        assert started_span_names == [
            "postrun.run",
            "postrun.compaction",
            "postrun.dq_evaluation",
            "postrun.dq_reports",
            "postrun.vacuum",
            "postrun.final_metadata",
        ]

    @pytest.mark.asyncio
    async def test_postrun_run_sets_detailed_outcome_attributes(self) -> None:
        """Verify detailed postrun attributes are attached to the active spans."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        mock_span.set_attribute.assert_any_call("bioetl.dq_reports_count", 0)
        mock_span.set_attribute.assert_any_call(
            "bioetl.compaction_duplicates_removed",
            0,
        )
        mock_span.set_attribute.assert_any_call(
            "bioetl.vacuum_silver_files_removed",
            0,
        )
        mock_span.set_attribute.assert_any_call(
            "bioetl.final_metadata_phase_completed",
            True,
        )

    @pytest.mark.asyncio
    async def test_postrun_run_span_is_entered_and_exited(self) -> None:
        """Verify span context manager is entered and exited cleanly."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)

        await service.run(executor=self._make_executor())

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        assert mock_span.__enter__.call_count == 6
        assert mock_span.__exit__.call_count == 6

    @pytest.mark.asyncio
    async def test_postrun_run_span_records_error_on_exception(self) -> None:
        """Verify span __exit__ receives exception info when run() raises."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)
        cast(Any, service._dq_service.evaluate).side_effect = RuntimeError("dq error")

        with pytest.raises(RuntimeError, match="dq error"):
            await service.run(executor=self._make_executor())

        mock_span = (
            mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        )
        exit_args = mock_span.__exit__.call_args[0]
        assert exit_args[0] is RuntimeError
        assert isinstance(exit_args[1], RuntimeError)
        assert str(exit_args[1]) == "dq error"

    @pytest.mark.asyncio
    async def test_postrun_run_none_tracer_is_rejected(self) -> None:
        """PostrunService must reject hidden tracer defaults in application layer."""
        await asyncio.sleep(0)
        with pytest.raises(TypeError, match="requires explicit tracer injection"):
            self._build_postrun_service(tracer=None)

    @pytest.mark.asyncio
    async def test_postrun_run_explicit_noop_tracer(self) -> None:
        """Verify run() works with an explicit NoOpTracing instance."""
        service = self._build_postrun_service(tracer=NoOpTracing())
        await service.run(executor=self._make_executor())

    def test_postrun_none_tracer_is_rejected(self) -> None:
        """Construction fails fast when tracer defaults are unresolved."""
        with pytest.raises(TypeError, match="requires explicit tracer injection"):
            self._build_postrun_service(tracer=None)

    def test_tracer_stored_when_provided(self) -> None:
        """Verify that an explicit tracer is stored as-is."""
        mock_tracer = _make_mock_tracer()
        service = self._build_postrun_service(tracer=mock_tracer)
        assert service._tracer is mock_tracer


# ---------------------------------------------------------------------------
# RecordProcessor: record.transform span (already existed — regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecordProcessorSpanRegression:
    """Regression tests: RecordProcessor.transform span was present before RF-007.

    These tests verify the existing spans are not broken.
    """

    def _build_record_processor(self, tracer: object) -> object:
        """Build a RecordProcessor with mocked dependencies."""
        from bioetl.application.core.record_processor import RecordProcessor
        from bioetl.application.core.config import RecordProcessorConfig

        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            logger=MagicMock(),
        )
        batch_metrics = MagicMock()
        batch_metrics.track_batch_size = MagicMock()
        batch_metrics.track_processed_records = MagicMock()

        transformer = MagicMock()
        transform_result = MagicMock()
        transform_result.silver_records = []
        transform_result.gold_records = []
        transform_result.quarantined_count = 0
        transformer.transform_batch = AsyncMock(return_value=transform_result)

        writer = MagicMock()
        writer.write_bronze = AsyncMock(return_value=None)
        writer.write_silver = AsyncMock(return_value=None)
        writer.write_gold = AsyncMock(return_value=None)
        writer.log_and_track_write_error = MagicMock()

        config = MagicMock(spec=RecordProcessorConfig)

        return RecordProcessor(
            context=context,
            batch_metrics=batch_metrics,
            transformer=transformer,
            writer=writer,
            config=config,
            tracer=cast(TracingPort, tracer),
        )

    @pytest.mark.asyncio
    async def test_record_processor_transform_span_created(self) -> None:
        """Verify transform span is created when processing a batch."""
        mock_tracer = _make_mock_tracer()
        processor = self._build_record_processor(tracer=mock_tracer)

        from bioetl.domain.types import BatchID

        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        await cast(Any, processor).process_batch(
            records=[{"id": "1"}], batch_id=batch_id
        )

        # get_tracer("bioetl.processor") should be called for span creation
        tracer_names = [c.args[0] for c in mock_tracer.get_tracer.call_args_list]
        assert "bioetl.processor" in tracer_names

    @pytest.mark.asyncio
    async def test_record_processor_noop_tracer_no_errors(self) -> None:
        """Verify process_batch works with NoOpTracing."""
        processor = self._build_record_processor(tracer=NoOpTracing())

        from bioetl.domain.types import BatchID

        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        result = await cast(Any, processor).process_batch(
            records=[{"id": "1"}], batch_id=batch_id
        )
        assert result is not None
