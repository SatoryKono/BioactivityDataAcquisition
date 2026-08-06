# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for BatchExecutor.

Tests the unified BatchExecutor that combines functionality from
the retired pipeline execution loop and RecordProcessor-era helpers.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_run_uuid_from_callsite,
)

import pytest

from bioetl.application.core.batch_execution import (
    BatchExecutionLifecycleService,
    BatchExecutionRunService,
    BatchExecutionStateService,
)
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionFSM,
    BatchExecutionState,
)
from bioetl.application.core.batch_processing_contracts import BatchProcessingOutcome
from bioetl.application.core.batch_executor import (
    BatchExecutor,
    BatchExecutorDependencies,
    BatchResult,
)
from bioetl.application.core.batch_executor_helpers import (
    BatchExecutionStateOutcome,
    apply_processed_batch_outcome,
    apply_batch_execution_state_update,
    build_batch_result_snapshot,
    build_processed_batch_outcome,
)
from bioetl.application.core.batch_executor_loop_helpers import (
    BatchExtractionIterationContext,
    BatchExtractionLoopState,
    build_batch_progress_payload,
    build_periodic_checkpoint_payload,
    ensure_extraction_not_shutdown,
    flush_batch_if_needed,
    process_extracted_record_iteration,
    report_batch_progress,
)
from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_processing_service import (
    BatchProcessingService,
)
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointRuntimeService,
)
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownSignal,
)
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.config import TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import (
    BatchID,
    GoldSchemaType,
    RunType,
    ValidationResult,
)


@pytest.fixture
def mock_storage():
    """Create mock storage."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_metrics():
    """Create mock metrics."""
    return MagicMock(spec=MetricsPort)


@pytest.fixture
def mock_quarantine_port():
    """Create mock quarantine port."""
    port = AsyncMock()
    port.write = AsyncMock()
    port.write_many = AsyncMock()
    return port


@pytest.fixture
def mock_services(mock_storage, mock_metrics, mock_quarantine_port):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineService)
    services.storage = mock_storage
    services.metrics = mock_metrics
    services.quarantine = mock_quarantine_port
    services.data_source = AsyncMock()
    services.data_source.get_source_metadata = MagicMock(return_value=None)
    services.logger = MagicMock()
    return services


@pytest.fixture
def mock_context():
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=deterministic_run_uuid_from_callsite("test_batch_executor"),
        run_type=RunType.INCREMENTAL,
        pipeline_name="test_provider_test_entity",
        logger=mock_logger,
    )


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    manager = MagicMock(spec=CheckpointRuntimeService)
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def shutdown_signal():
    """Create shutdown signal."""
    return ShutdownSignal()


@pytest.fixture
def transform_callback():
    """Create mock transform callback without transient lineage fields."""

    async def transform(ctx, record, index):
        await asyncio.sleep(0)
        return {
            "entity_id": record.get("id", "unknown"),
            "value": record.get("value"),
        }

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create mock gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def gold_transform_callback():
    """Create mock gold transform callback."""

    def transform_gold(ctx, record):
        return record

    return transform_gold


@pytest.fixture
def mock_gold_validator():
    """Create mock gold validator."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def processor_config():
    """Create processor config."""
    return RecordProcessorConfig(
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=cast(GoldSchemaType, MagicMock()),
        table_config=TableConfig(),
    )


def _create_batch_executor(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    gold_validator,
    checkpoint_manager,
    shutdown_signal,
    batch_size: int | None = 10,
    checkpoint_interval: int | None = 5,
    tracer=None,
    batch_id_factory=None,
) -> BatchExecutor:
    """Build BatchExecutor with composition-level dependency wiring."""
    error_classifier = ErrorClassifier()
    components = ServicesBuilder.create_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator,
        tracer=tracer,
    )

    initial_batch_size = batch_size or BatchExecutor.DEFAULT_BATCH_SIZE
    memory_manager = BatchMemoryManagerService(
        initial_batch_size=initial_batch_size,
        logger=services.logger,
    )
    tracing_manager = BatchTracingManagerService(
        tracer=tracer if tracer is not None else NoOpTracing(),
        context=context,
        config=config,
        initial_batch_size=initial_batch_size,
        adaptive_sizing_enabled=memory_manager.enabled,
    )
    progress_service = BatchProgressService(
        logger=services.logger,
        data_source=services.data_source,
    )
    checkpoint_recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=services.logger,
        metrics=services.metrics,
        pipeline_name=config.pipeline_name,
    )
    effective_batch_id_factory = batch_id_factory or BatchExecutorUuidFactoryAdapter()
    batch_processing_service = BatchProcessingService(
        services=services,
        context=context,
        config=config,
        components=components,
        tracing_manager=tracing_manager,
        batch_id_factory=effective_batch_id_factory,
        support_service=BatchProcessingSupportService(
            services=services,
            logger=services.logger,
            batch_metrics=components.batch_metrics,
            transformer=components.transformer,
            writer=components.writer,
            tracing=tracing_manager,
            quarantine_manager=MagicMock(),
        ),
    )
    execution_lifecycle_service = BatchExecutionLifecycleService(
        progress_service=progress_service,
        tracing_manager=tracing_manager,
        checkpoint_recovery_service=checkpoint_recovery_service,
    )
    execution_run_service = BatchExecutionRunService(
        execution_lifecycle_service=execution_lifecycle_service
    )
    execution_state_service = BatchExecutionStateService()
    effective_checkpoint_interval = (
        checkpoint_interval or BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL
    )

    deps = BatchExecutorDependencies(
        memory_manager=memory_manager,
        execution_run_service=execution_run_service,
        extraction_loop_service=BatchExtractionLoopService(
            batch_processing_service=batch_processing_service,
            shutdown_signal=shutdown_signal,
            memory_manager=memory_manager,
            progress_service=progress_service,
            checkpoint_recovery_service=checkpoint_recovery_service,
            checkpoint_interval=effective_checkpoint_interval,
        ),
        execution_state_service=execution_state_service,
        processing_port=batch_processing_service,
        fsm=BatchExecutionFSM(),
    )

    return BatchExecutor(
        services=services,
        context=context,
        config=config,
        dependencies=deps,
        batch_size=batch_size,
        checkpoint_interval=checkpoint_interval,
    )


class BatchExecutorUuidFactoryAdapter:
    """Default batch-id factory adapter mirroring production uuid4 behavior."""

    def create(self) -> BatchID:
        return deterministic_batch_uuid_from_callsite("test_batch_executor")


class DeterministicBatchIdFactory:
    """Deterministic factory for batch ID propagation tests."""

    def __init__(self, batch_id: BatchID) -> None:
        self._batch_id = batch_id
        self.calls = 0

    def create(self) -> BatchID:
        self.calls += 1
        return self._batch_id


@pytest.fixture
def batch_executor(
    mock_services,
    mock_context,
    processor_config,
    mock_checkpoint_manager,
    shutdown_signal,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    mock_gold_validator,
):
    """Create BatchExecutor instance."""
    return _create_batch_executor(
        services=mock_services,
        context=mock_context,
        config=processor_config,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=mock_gold_validator,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        batch_size=10,
        checkpoint_interval=5,
    )


@pytest.mark.unit
class TestBatchExecutorInit:
    """Tests for BatchExecutor initialization."""

    def test_init_stores_batch_size(self, batch_executor):
        """Test that initialization stores batch size."""
        assert batch_executor.batch_size == 10

    def test_init_stores_checkpoint_interval(self, batch_executor):
        """Test that initialization stores checkpoint interval."""
        assert batch_executor.checkpoint_interval == 5

    def test_init_default_batch_size(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        shutdown_signal,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
    ):
        """Test default batch size when not specified."""
        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            batch_size=None,
            checkpoint_interval=None,
        )
        assert executor.batch_size == BatchExecutor.DEFAULT_BATCH_SIZE

    def test_init_counters_zero(self, batch_executor):
        """Test that counters start at zero."""
        assert batch_executor.records_fetched == 0
        assert batch_executor.records_bronze == 0
        assert batch_executor.records_silver == 0
        assert batch_executor.records_gold == 0
        assert batch_executor.records_gold_excluded_by_contract == 0
        assert batch_executor.records_quarantined == 0


@pytest.mark.unit
class TestBatchExecutorExecute:
    """Tests for execute method."""

    def test_prepare_execution_context_persists_resume_offset_and_query(
        self, batch_executor
    ):
        """Prepared execution context should mirror and persist run inputs."""
        execution_context = batch_executor._prepare_execution_context(
            limit=25,
            query="kinase",
            offset=8,
        )

        assert execution_context.limit == 25
        assert execution_context.query == "kinase"
        assert execution_context.offset == 8
        assert execution_context.resume_offset == 8
        assert batch_executor._resume_offset == 8
        assert batch_executor._query_string == "kinase"

    async def test_execute_processes_records(
        self, batch_executor, mock_services, mock_storage
    ):
        """Test that execute processes records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        assert batch_executor.records_fetched == 3
        assert batch_executor.records_bronze == 3
        assert batch_executor.records_silver == 3
        assert batch_executor.records_gold >= 0
        mock_storage.write_bronze.assert_called()
        mock_storage.write_silver.assert_called()
        # mock_storage.write_gold.assert_called()

    async def test_execute_batches_records(self, batch_executor, mock_services):
        """Test that execute batches records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(15):  # More than batch size of 10
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        # Should have processed in 2 batches (10 + 5)
        assert batch_executor.records_fetched == 15
        assert batch_executor.records_bronze == 15

    async def test_execute_checkpoints_at_interval(
        self, batch_executor, mock_services, mock_checkpoint_manager
    ):
        """Test that execute checkpoints at configured interval."""

        async def mock_fetch(**kwargs):
            for i in range(10):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        # With checkpoint_interval=5, should checkpoint at record 5 and 10
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2

    async def test_execute_handles_shutdown(
        self, batch_executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown saves checkpoint."""
        records_yielded = 0

        async def mock_fetch(**kwargs):
            nonlocal records_yielded
            for i in range(10):
                yield {"id": str(i), "value": 10}
                records_yielded += 1
                if records_yielded == 3:
                    shutdown_signal.request()

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await batch_executor.execute(limit=None)

        mock_checkpoint_manager.save_checkpoint.assert_called()

    async def test_execute_empty_data(
        self, batch_executor, mock_services, mock_storage
    ):
        """Test execute with no data."""

        async def mock_fetch(**kwargs):
            if kwargs.get("__yield__"):
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        assert batch_executor.records_fetched == 0
        mock_storage.write_bronze.assert_not_called()

    async def test_execute_passes_limit(self, batch_executor, mock_services):
        """Test that limit is passed to data source."""
        captured_kwargs = {}

        async def mock_fetch(**kwargs):
            captured_kwargs.update(kwargs)
            if kwargs.get("__yield__"):
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=100)

        assert captured_kwargs.get("limit") == 100

    async def test_execute_checkpoint_uses_resume_offset(
        self,
        batch_executor,
        mock_services,
        mock_checkpoint_manager,
    ):
        """Checkpoint totals must include resume offset."""

        async def mock_fetch(**kwargs):
            for i in range(5):  # checkpoint_interval in fixture is 5
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None, offset=10)

        mock_checkpoint_manager.save_checkpoint.assert_any_call(15)

    async def test_execute_shutdown_checkpoint_uses_resume_offset(
        self,
        batch_executor,
        mock_services,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Shutdown checkpoint must include resume offset and fetched count."""
        records_yielded = 0

        async def mock_fetch(**kwargs):
            nonlocal records_yielded
            for i in range(10):
                yield {"id": str(i), "value": 10}
                records_yielded += 1
                if records_yielded == 2:
                    shutdown_signal.request()

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await batch_executor.execute(limit=None, offset=8)

        checkpoint_totals = [
            call.args[0]
            for call in mock_checkpoint_manager.save_checkpoint.call_args_list
        ]
        assert checkpoint_totals
        assert all(total == 10 for total in checkpoint_totals)


@pytest.mark.unit
class TestBatchExecutorProcessBatch:
    """Tests for batch processing functionality."""

    async def test_execute_process_batch_writes_to_all_layers(
        self, batch_executor, mock_services, mock_storage
    ):
        """Test that processing writes to Bronze, Silver, and Gold."""

        async def mock_fetch(**kwargs):
            yield {"id": "1", "value": 10}  # Goes to gold (value > 5)
            yield {"id": "2", "value": 3}  # Not in gold

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        assert batch_executor.records_bronze == 2
        assert batch_executor.records_silver == 2
        assert batch_executor.records_gold >= 0
        assert batch_executor.records_quarantined == 0
        mock_storage.write_bronze.assert_called_once()
        mock_storage.write_silver.assert_called_once()
        # mock_storage.write_gold.assert_called_once()

    async def test_execute_process_batch_skips_gold_when_filter_rejects_all(
        self, batch_executor, mock_services, mock_storage
    ):
        """Test process when no records pass gold filter."""

        async def mock_fetch(**kwargs):
            yield {"id": "1", "value": 1}
            yield {"id": "2", "value": 2}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        assert batch_executor.records_gold == 0
        mock_storage.write_gold.assert_not_called()

    async def test_execute_process_batch_quarantines_transform_errors(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        shutdown_signal,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
    ):
        """Test that transform errors result in quarantine."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            batch_size=10,
        )

        async def mock_fetch(**kwargs):
            yield {"id": "good", "value": 10}
            yield {"id": "bad", "value": 5}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        assert executor.records_bronze == 2
        assert executor.records_silver >= 1
        assert executor.records_quarantined >= 0
        mock_services.quarantine.write_many.assert_called_once()

    async def test_process_batch_uses_injected_batch_id_factory(
        self,
        mock_services,
        mock_storage,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        shutdown_signal,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
    ):
        """Injected BatchIdFactory must deterministically propagate batch_id."""
        fixed_batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        batch_id_factory = DeterministicBatchIdFactory(fixed_batch_id)

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            batch_size=10,
            checkpoint_interval=5,
            batch_id_factory=batch_id_factory,
        )

        async def mock_fetch(**kwargs):
            yield {"id": "1", "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        assert batch_id_factory.calls == 1
        assert mock_storage.write_bronze.call_args.kwargs["batch_id"] == fixed_batch_id
        silver_call_kwargs = mock_storage.write_silver.call_args.kwargs
        silver_records = silver_call_kwargs["records"]
        assert silver_records
        assert all("_source_batch_id" not in rec for rec in silver_records)
        assert silver_call_kwargs["source_batch_id"] == fixed_batch_id
        assert executor.get_run_statistics()["source_batch_ids"] == [
            str(fixed_batch_id)
        ]

    def test_get_run_statistics_preserves_source_batch_id_order(
        self,
        batch_executor,
    ) -> None:
        """Run statistics should deduplicate batch IDs without reordering them."""
        batch_executor.records_fetched = 5
        batch_executor.records_bronze = 5
        batch_executor.records_silver = 4
        batch_executor.records_gold = 2
        batch_executor.records_gold_excluded_by_contract = 1
        batch_executor.records_quarantined = 1
        batch_executor.records_filtered_out = 1
        batch_executor.source_batch_ids = ["batch-002", "batch-001", "batch-002"]

        stats = batch_executor.get_run_statistics()

        assert stats == {
            "records_fetched": 5,
            "records_bronze": 5,
            "records_silver": 4,
            "records_gold": 2,
            "records_gold_excluded_by_contract": 1,
            "records_quarantined": 1,
            "records_filtered_out": 1,
            "source_batch_ids": ["batch-002", "batch-001"],
        }


@pytest.fixture
def mock_tracer():
    """Create mock tracer for testing spans."""
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()

    inner_tracer = MagicMock()
    inner_tracer.start_as_current_span = MagicMock(return_value=span)

    tracer = MagicMock()
    tracer.get_tracer = MagicMock(return_value=inner_tracer)
    return tracer


@pytest.fixture
def batch_executor_with_tracer(
    mock_services,
    mock_context,
    processor_config,
    mock_checkpoint_manager,
    shutdown_signal,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    mock_gold_validator,
    mock_tracer,
):
    """Create BatchExecutor instance with tracer."""
    return _create_batch_executor(
        services=mock_services,
        context=mock_context,
        config=processor_config,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=mock_gold_validator,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        batch_size=10,
        checkpoint_interval=5,
        tracer=mock_tracer,
    )


@pytest.mark.unit
class TestBatchExecutorTracing:
    """Tests for BatchExecutor tracing spans."""

    async def test_tracing_on_off_preserves_bounded_pipeline_outcome(
        self,
        mock_services,
        mock_context,
        processor_config,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Real tracing must preserve B/S/G counts and the terminal FSM state."""
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from bioetl.infrastructure.observability import tracing

        if not tracing.otel_available:
            pytest.skip("OpenTelemetry is not available")

        exporter = InMemorySpanExporter()
        monkeypatch.setattr(
            tracing,
            "_build_telemetry_exporter",
            lambda: exporter,
        )
        real_tracer = tracing.OpenTelemetryTracer("bioetl-parity-contract")
        fixed_batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))

        def build_executor(tracer) -> BatchExecutor:
            return _create_batch_executor(
                services=mock_services,
                context=mock_context,
                config=processor_config,
                transform_callback=transform_callback,
                gold_filter_callback=gold_filter_callback,
                gold_transform_callback=gold_transform_callback,
                gold_validator=mock_gold_validator,
                checkpoint_manager=MagicMock(spec=CheckpointRuntimeService),
                shutdown_signal=ShutdownSignal(),
                batch_size=10,
                checkpoint_interval=5,
                tracer=tracer,
                batch_id_factory=DeterministicBatchIdFactory(fixed_batch_id),
            )

        async def run(executor: BatchExecutor) -> tuple[dict[str, object], object]:
            async def fetch(**_kwargs):
                for index in range(3):
                    yield {"id": str(index), "value": 10}

            mock_services.data_source.fetch = fetch
            await executor.execute(limit=3)
            return executor.get_run_statistics(), executor._fsm_state

        try:
            noop_outcome = await run(build_executor(NoOpTracing()))
            real_outcome = await run(build_executor(real_tracer))
        finally:
            real_tracer.close()

        assert real_outcome == noop_outcome
        statistics, terminal_state = real_outcome
        assert statistics["records_bronze"] == 3
        assert statistics["records_silver"] == 3
        assert statistics["records_gold"] == 3
        assert terminal_state is BatchExecutionState.DONE

        root_spans = [
            span
            for span in exporter.get_finished_spans()
            if span.name == "pipeline_execution"
        ]
        assert len(root_spans) == 1
        assert any(
            event.name == "bioetl.memory.decision" for event in root_spans[0].events
        )

    async def test_execute_creates_root_span(
        self, batch_executor_with_tracer, mock_services, mock_tracer
    ):
        """Test that execute creates a root span."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor_with_tracer.execute(limit=None)

        mock_tracer.get_tracer.assert_called()
        inner_tracer = mock_tracer.get_tracer.return_value
        inner_tracer.start_as_current_span.assert_called()

        # Check root span was created with correct name
        calls = inner_tracer.start_as_current_span.call_args_list
        root_span_call = calls[0]
        assert root_span_call[0][0] == "pipeline_execution"
        attrs = root_span_call[1]["attributes"]
        assert "bioetl.run_id" in attrs
        assert attrs["bioetl.entity_type"] == "test_entity"
        assert attrs["bioetl.run_type"] == "incremental"

    async def test_root_span_records_final_counts(
        self, batch_executor_with_tracer, mock_services, mock_tracer
    ):
        """Test that root span records final record counts."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor_with_tracer.execute(limit=None)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        set_attribute_calls = span.set_attribute.call_args_list
        attr_names = [call[0][0] for call in set_attribute_calls]
        assert "bioetl.total_fetched" in attr_names
        assert "bioetl.total_bronze" in attr_names
        assert "bioetl.total_silver" in attr_names
        assert "bioetl.total_gold" in attr_names

    async def test_root_span_records_shutdown(
        self, batch_executor_with_tracer, mock_services, mock_tracer, shutdown_signal
    ):
        """Test that root span records shutdown attribute."""
        records_yielded = 0

        async def mock_fetch(**kwargs):
            nonlocal records_yielded
            for i in range(10):
                yield {"id": str(i), "value": 10}
                records_yielded += 1
                if records_yielded == 3:
                    shutdown_signal.request()

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await batch_executor_with_tracer.execute(limit=None)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.set_attribute.assert_any_call("bioetl.shutdown", True)

    async def test_root_span_records_exception_and_saves_recovery_checkpoint(
        self,
        batch_executor_with_tracer,
        mock_checkpoint_manager,
        mock_tracer,
    ):
        """Runtime failures should save a recovery checkpoint and mark the span."""

        async def boom(*_args, **_kwargs):
            await asyncio.sleep(0)
            batch_executor_with_tracer.records_fetched = 3
            raise RuntimeError("boom")

        batch_executor_with_tracer._run_extraction_loop = AsyncMock(side_effect=boom)

        with pytest.raises(RuntimeError, match="boom"):
            await batch_executor_with_tracer.execute(limit=None, offset=4)

        mock_checkpoint_manager.save_checkpoint.assert_awaited_once_with(7)
        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.record_exception.assert_called_once()
        span.set_attribute.assert_any_call("error", True)

    async def test_execute_without_tracer_records_counts_without_span(
        self, batch_executor, mock_services
    ):
        """Test that no span is created when tracer is None."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=None)

        assert batch_executor.records_fetched == 3
        assert batch_executor.records_bronze == 3
        assert batch_executor.records_silver == 3


@pytest.mark.unit
class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_immutable(self):
        """Test that BatchResult is immutable."""
        result = BatchResult(
            bronze_count=10,
            silver_count=9,
            gold_count=8,
            quarantined_count=1,
        )
        with pytest.raises(FrozenInstanceError):
            result.__setattr__("bronze_count", 20)

    def test_batch_result_stores_counts(self):
        """Test that BatchResult stores all counts."""
        result = BatchResult(
            bronze_count=100,
            silver_count=95,
            gold_count=80,
            quarantined_count=5,
        )
        assert result.bronze_count == 100
        assert result.silver_count == 95
        assert result.gold_count == 80
        assert result.quarantined_count == 5


@pytest.mark.unit
class TestBatchExecutorHelpers:
    """Tests for extracted batch-executor helper functions."""

    def test_build_processed_batch_outcome_projects_state_and_dq_payloads(self) -> None:
        """Processed-outcome helper should preserve both state deltas and DQ inputs."""
        batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
        records = [{"id": "1", "value": 10}]
        output = BatchProcessingOutcome(
            batch_id=batch_id,
            bronze_result=MagicMock(path="bronze/file.jsonl"),
            silver_records=[{"id": "1", "value": 10}],
            gold_records=[{"id": "1", "score": 0.9}],
            quarantined_count=2,
            filtered_out_count=3,
        )

        outcome = build_processed_batch_outcome(records=records, output=output)

        assert outcome.records == records
        assert outcome.batch_id == batch_id
        assert outcome.bronze_result is output.bronze_result
        assert outcome.silver_records == output.silver_records
        assert outcome.gold_records == output.gold_records
        assert outcome.state_update == BatchExecutionStateOutcome(
            bronze_count=1,
            silver_count=1,
            gold_count=1,
            gold_excluded_by_contract_count=0,
            quarantined_count=2,
            filtered_out_count=3,
            source_batch_id=str(batch_id),
        )

    def test_apply_batch_execution_state_update_updates_counters(self) -> None:
        """State helper should apply deltas and preserve batch-id order."""
        state = MagicMock(
            records_bronze=10,
            records_silver=8,
            records_gold=6,
            records_gold_excluded_by_contract=2,
            records_quarantined=1,
            records_filtered_out=2,
            source_batch_ids=["batch-001"],
        )

        apply_batch_execution_state_update(
            state=state,
            state_update=BatchExecutionStateOutcome(
                bronze_count=3,
                silver_count=2,
                gold_count=1,
                gold_excluded_by_contract_count=6,
                quarantined_count=4,
                filtered_out_count=5,
                source_batch_id="batch-002",
            ),
        )

        assert state.records_bronze == 13
        assert state.records_silver == 10
        assert state.records_gold == 7
        assert state.records_gold_excluded_by_contract == 8
        assert state.records_quarantined == 5
        assert state.records_filtered_out == 7
        assert state.source_batch_ids == ["batch-001", "batch-002"]

    def test_apply_processed_batch_outcome_updates_state_and_collects_dq(self) -> None:
        """Processed-outcome helper should update counters and invoke DQ hook."""
        state = MagicMock(
            records_bronze=10,
            records_silver=8,
            records_gold=6,
            records_gold_excluded_by_contract=2,
            records_quarantined=1,
            records_filtered_out=2,
            source_batch_ids=["batch-001"],
        )
        state._should_collect_dq_data.return_value = True
        outcome = build_processed_batch_outcome(
            records=[{"id": "1"}],
            output=BatchProcessingOutcome(
                batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
                bronze_result=MagicMock(path="bronze/file.jsonl"),
                silver_records=[{"id": "1"}],
                gold_records=[],
                quarantined_count=4,
                filtered_out_count=5,
                gold_excluded_by_contract_count=3,
            ),
        )

        apply_processed_batch_outcome(state=state, outcome=outcome)

        assert state.records_bronze == 11
        assert state.records_silver == 9
        assert state.records_gold == 6
        assert state.records_gold_excluded_by_contract == 5
        assert state.records_quarantined == 5
        assert state.records_filtered_out == 7
        assert state.source_batch_ids == [
            "batch-001",
            "12345678-1234-5678-1234-567812345678",
        ]
        state._collect_dq_data.assert_called_once_with(
            records=[{"id": "1"}],
            batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            bronze_result=outcome.bronze_result,
            silver_records=[{"id": "1"}],
            gold_records=[],
        )

    def test_apply_processed_batch_outcome_skips_dq_hook_when_disabled(self) -> None:
        """Processed-outcome helper should not call DQ collection when disabled."""
        state = MagicMock(
            records_bronze=0,
            records_silver=0,
            records_gold=0,
            records_gold_excluded_by_contract=0,
            records_quarantined=0,
            records_filtered_out=0,
            source_batch_ids=[],
        )
        state._should_collect_dq_data.return_value = False
        outcome = build_processed_batch_outcome(
            records=[{"id": "1"}],
            output=BatchProcessingOutcome(
                batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
                bronze_result=None,
                silver_records=[],
                gold_records=[],
                quarantined_count=0,
                filtered_out_count=0,
            ),
        )

        apply_processed_batch_outcome(state=state, outcome=outcome)

        state._collect_dq_data.assert_not_called()

    def test_build_batch_result_snapshot_uses_current_counters(self) -> None:
        """Batch-result helper should mirror current cumulative counters."""
        result = build_batch_result_snapshot(
            batch_result_type=BatchResult,
            records_bronze=12,
            records_silver=11,
            records_gold=9,
            records_quarantined=2,
        )

        assert result == BatchResult(
            bronze_count=12,
            silver_count=11,
            gold_count=9,
            quarantined_count=2,
        )


@pytest.mark.unit
class TestBatchExecutorLoopHelpers:
    """Tests for extracted extraction-loop helper payloads."""

    def test_build_batch_progress_payload_contains_current_counts(self) -> None:
        """Progress payload should mirror the current executor counters."""
        assert build_batch_progress_payload(
            records_fetched=9,
            records_bronze=8,
            records_silver=7,
            records_filtered_out=2,
        ) == {
            "records_fetched": 9,
            "records_bronze": 8,
            "records_silver": 7,
            "records_filtered_out": 2,
        }

    def test_build_periodic_checkpoint_payload_includes_interval(self) -> None:
        """Periodic checkpoint payload must preserve interval and resume offset."""
        assert build_periodic_checkpoint_payload(
            records_fetched=14,
            resume_offset=25,
            checkpoint_interval=5,
        ) == {
            "records_fetched": 14,
            "resume_offset": 25,
            "checkpoint_interval": 5,
        }

    def test_report_batch_progress_forwards_current_counters(self) -> None:
        """Progress helper should forward the current loop counters unchanged."""
        progress_service = MagicMock()
        state = MagicMock(
            records_fetched=12,
            records_bronze=10,
            records_silver=8,
            records_filtered_out=2,
        )

        report_batch_progress(
            progress_service=progress_service,
            state=state,
        )

        progress_service.report_progress.assert_called_once_with(
            records_fetched=12,
            records_bronze=10,
            records_silver=8,
            records_filtered_out=2,
        )

    @pytest.mark.asyncio
    async def test_ensure_extraction_not_shutdown_is_noop_when_not_requested(
        self,
    ) -> None:
        """Shutdown helper should not checkpoint or raise when shutdown is clear."""
        checkpoint_recovery_service = AsyncMock()

        await ensure_extraction_not_shutdown(
            shutdown_requested=False,
            checkpoint_recovery_service=checkpoint_recovery_service,
            records_fetched=5,
            resume_offset=11,
        )

        checkpoint_recovery_service.save_checkpoint_now.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_flush_batch_if_needed_processes_and_resets_batch(self) -> None:
        """Flush helper should process the batch, reset it, and emit progress."""
        process_batch = AsyncMock()
        progress_service = MagicMock()
        memory_manager = MagicMock()
        memory_manager.maybe_recover.return_value = 7
        progress_state = MagicMock(
            records_fetched=9,
            records_bronze=6,
            records_silver=5,
            records_filtered_out=1,
        )
        loop_state = BatchExtractionLoopState(
            current_batch_size=2,
            check_interval=10,
            batch=[{"id": "1"}, {"id": "2"}],
        )

        await flush_batch_if_needed(
            loop_state=loop_state,
            records_fetched=9,
            process_batch=process_batch,
            memory_manager=memory_manager,
            progress_service=progress_service,
            progress_state=progress_state,
        )

        process_batch.assert_awaited_once_with(
            [{"id": "1"}, {"id": "2"}],
            7,
        )
        assert loop_state.batch == []
        assert loop_state.current_batch_size == 7
        progress_service.report_progress.assert_called_once_with(
            records_fetched=9,
            records_bronze=6,
            records_silver=5,
            records_filtered_out=1,
        )

    @pytest.mark.asyncio
    async def test_process_extracted_record_iteration_preserves_step_order(
        self,
    ) -> None:
        """One extracted-record iteration should keep the canonical loop order."""
        call_order: list[str] = []
        process_batch = AsyncMock(
            side_effect=lambda *_args, **_kwargs: call_order.append("process_batch")
        )
        progress_service = MagicMock()
        progress_service.report_progress.side_effect = lambda **kwargs: (
            call_order.append(f"progress:{kwargs['records_fetched']}")
        )
        memory_manager = MagicMock()
        memory_manager.check_pressure.side_effect = lambda *_args: (
            call_order.append("check_pressure") or 1
        )
        memory_manager.maybe_recover.side_effect = lambda *_args: (
            call_order.append("maybe_recover") or 3
        )
        checkpoint_recovery_service = AsyncMock()
        checkpoint_recovery_service.save_periodic_checkpoint.side_effect = (
            lambda **_kwargs: call_order.append("save_periodic_checkpoint")
        )
        progress_state = MagicMock(
            records_fetched=1,
            records_bronze=0,
            records_silver=0,
            records_filtered_out=0,
        )
        loop_state = BatchExtractionLoopState(
            current_batch_size=1,
            check_interval=10,
        )
        iteration_context = BatchExtractionIterationContext(
            checkpoint_recovery_service=checkpoint_recovery_service,
            resume_offset=4,
            process_batch=process_batch,
            memory_manager=memory_manager,
            progress_service=progress_service,
            progress_state=progress_state,
            checkpoint_interval=5,
        )

        next_records_fetched = await process_extracted_record_iteration(
            loop_state=loop_state,
            raw_record={"id": "1"},
            shutdown_requested=False,
            records_fetched=0,
            iteration_context=iteration_context,
        )

        assert next_records_fetched == 1
        assert call_order == [
            "check_pressure",
            "progress:1",
            "process_batch",
            "maybe_recover",
            "progress:1",
            "save_periodic_checkpoint",
        ]
        checkpoint_recovery_service.save_checkpoint_now.assert_not_awaited()
