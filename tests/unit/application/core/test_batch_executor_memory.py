"""Unit tests for BatchExecutor memory management."""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_execution import (
    BatchExecutionLifecycleService,
    BatchExecutionRunService,
    BatchExecutionStateService,
)
from bioetl.application.core.batch_executor import (
    BatchExecutor,
    BatchExecutorDependencies,
)
from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_processing_service import BatchProcessingService
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.lifecycle.batch_fsm import BatchExecutionFSM
from bioetl.application.core.lifecycle.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.config import MemoryConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import (
    MemoryMonitorPort,
    MetricsPort,
)
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import (
    BatchID,
    GoldSchemaType,
    RunID,
    RunType,
    ValidationResult,
)


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineService)
    services.storage = AsyncMock()
    services.metrics = MagicMock(spec=MetricsPort)
    services.quarantine = AsyncMock()
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
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    manager = MagicMock(spec=CheckpointManager)
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def processor_config():
    """Create processor config."""
    return RecordProcessorConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=cast(GoldSchemaType, MagicMock()),
        table_config=TableConfig(),
    )


@pytest.fixture
def callbacks():
    """Create mock callbacks."""

    async def transform(ctx, record, index):
        await asyncio.sleep(0)
        return {
            "entity_id": str(index),
            "_run_id": str(ctx.run_id),
            "_run_type": ctx.run_type.value,
            "_ingestion_ts": ctx.started_at.isoformat(),
        }

    return {
        "transform": transform,
        "gold_filter": lambda c, r: True,
        "gold_transform": lambda c, r: r,
    }


@pytest.fixture
def mock_gold_validator():
    """Create mock gold validator."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def memory_monitor():
    """Create mock memory monitor."""
    monitor = MagicMock(spec=MemoryMonitorPort)
    monitor.get_recommended_batch_size = MagicMock(return_value=100)
    return monitor


@pytest.fixture
def memory_config():
    """Create memory config."""
    return MemoryConfig(
        enable_adaptive_sizing=True,
        max_batch_memory_mb=10,
        min_batch_size=10,
        check_interval_records=5,
    )


def _create_batch_executor(
    *,
    services: PipelineService,
    context: PipelineContext,
    config: RecordProcessorConfig,
    callbacks: dict,
    gold_validator,
    checkpoint_manager,
    shutdown_signal: ShutdownSignal | None = None,
    batch_size: int | None = None,
    checkpoint_interval: int | None = None,
    memory_monitor: MemoryMonitorPort | None = None,
    memory_config: MemoryConfig | None = None,
) -> BatchExecutor:
    """Build BatchExecutor with composition-level dependency wiring."""
    if shutdown_signal is None:
        shutdown_signal = ShutdownSignal()

    error_classifier = ErrorClassifier()
    components = ServicesBuilder.create_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=callbacks["transform"],
        gold_filter_callback=callbacks["gold_filter"],
        gold_transform_callback=callbacks["gold_transform"],
        gold_validator=gold_validator,
    )

    initial_batch_size = batch_size or BatchExecutor.DEFAULT_BATCH_SIZE
    mem_manager = BatchMemoryManagerService(
        initial_batch_size=initial_batch_size,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        logger=services.logger,
    )
    tracing_manager = BatchTracingManagerService(
        tracer=NoOpTracing(),
        context=context,
        config=config,
        initial_batch_size=initial_batch_size,
        adaptive_sizing_enabled=mem_manager.enabled,
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
    batch_id_factory = BatchExecutorUuidFactoryAdapter()
    batch_processing_service = BatchProcessingService(
        services=services,
        context=context,
        config=config,
        components=components,
        tracing_manager=tracing_manager,
        batch_id_factory=batch_id_factory,
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

    deps = BatchExecutorDependencies(
        memory_manager=mem_manager,
        execution_run_service=execution_run_service,
        extraction_loop_service=BatchExtractionLoopService(
            batch_processing_service=batch_processing_service,
            shutdown_signal=shutdown_signal,
            memory_manager=mem_manager,
            progress_service=progress_service,
            checkpoint_recovery_service=checkpoint_recovery_service,
            checkpoint_interval=checkpoint_interval
            or BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL,
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
        return BatchID(uuid4())


class TestBatchExecutorMemory:
    """Tests for BatchExecutor memory management."""

    def test_init_adaptive_sizing_enabled(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
        memory_monitor,
    ):
        """Test that adaptive sizing is enabled when monitor provided."""
        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            memory_monitor=memory_monitor,
        )
        assert executor._memory.enabled is True

    @pytest.mark.asyncio
    async def test_check_memory_pressure_reduces_size(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
        memory_monitor,
    ):
        """Test that batch size is reduced under memory pressure."""
        memory_monitor.get_recommended_batch_size.return_value = 50

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            batch_size=100,
            memory_monitor=memory_monitor,
            memory_config=MemoryConfig(
                enable_adaptive_sizing=True, check_interval_records=1
            ),
        )

        # Mock fetch to yield records
        async def mock_fetch(**kwargs):
            await asyncio.sleep(0)
            for i in range(10):
                yield {"id": i}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # Verify batch size was reduced
        assert executor._memory.batch_size_reductions > 0
        assert executor._memory.min_batch_size_used <= 50
        mock_services.logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_recover_batch_size(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
        memory_monitor,
    ):
        """Test that batch size recovers when pressure relieved."""
        # Initial pressure then relief - provide enough values for all checks
        # 20 records, check every 1 record -> ~20 checks
        memory_monitor.get_recommended_batch_size.side_effect = [50] * 10 + [100] * 20

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            batch_size=100,
            memory_monitor=memory_monitor,
            memory_config=MemoryConfig(
                enable_adaptive_sizing=True, check_interval_records=1
            ),
        )

        async def mock_fetch(**kwargs):
            await asyncio.sleep(0)
            for i in range(20):
                yield {"id": i}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # Check interaction with monitor
        assert memory_monitor.get_recommended_batch_size.call_count >= 2

    @pytest.mark.asyncio
    async def test_estimate_batch_size_from_config(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
        memory_config,
    ):
        """Test estimation from config without monitor."""
        await asyncio.sleep(0)
        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            batch_size=20000,  # Large initial size
            memory_config=memory_config,  # Max 10MB -> ~10000 records
        )

        # Force a check
        new_size = executor._memory._estimate_from_config(20000)
        assert new_size <= 10000  # Should be capped by memory config

    @pytest.mark.asyncio
    async def test_dq_data_collection(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
    ):
        """Test collection of DQ data."""
        mock_dq_service = MagicMock()
        mock_services.dq_report_service = mock_dq_service

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            batch_size=10,
        )

        async def mock_fetch(**kwargs):
            await asyncio.sleep(0)
            yield {"id": 1, "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # Check internal storage
        assert len(executor._bronze_records_for_dq) == 1
        assert len(executor._silver_records_for_dq) == 1
        assert len(executor._gold_records_for_dq) == 1
        assert len(executor._source_batch_ids) == 1

        # Check context generation
        context = executor.get_dq_context()
        assert context is not None
        assert context.bronze_records is not None
        assert context.provider == "test_provider"

    def test_build_dataframe_from_records_normalizes_mixed_nested_and_string_columns(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
    ) -> None:
        """Mixed dict/string values in one column should not crash Polars build."""
        try:
            import polars as pl
        except ImportError:
            pytest.skip("polars not installed")

        mock_services.dq_report_service = MagicMock()
        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            batch_size=10,
        )

        records = [
            {
                "entity_id": "1",
                "assay_classifications": {
                    "assay_class_id": 322,
                    "bao_id": None,
                    "class_type": "In vivo efficacy",
                    "l1": "NERVOUS SYSTEM",
                    "l2": "Anti-Depressant Activity",
                    "l3": "General Hypothermia",
                    "source": "phenotype",
                },
            },
            {
                "entity_id": "2",
                "assay_classifications": '{"assay_class_id":322,"source":"phenotype"}',
            },
        ]

        df = executor._build_dataframe_from_records(records)
        assert df is not None
        assert isinstance(df, pl.DataFrame)
        assert df["assay_classifications"].dtype == pl.Utf8

    def test_get_dq_context_no_service(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
    ):
        """Test get_dq_context returns None when service not available."""
        mock_services.dq_report_service = None  # explicit None

        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
        )

        assert executor.get_dq_context() is None

    @pytest.mark.asyncio
    async def test_process_public_api(
        self,
        mock_services,
        mock_context,
        processor_config,
        mock_checkpoint_manager,
        callbacks,
        mock_gold_validator,
    ):
        """Test public process() method."""
        executor = _create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            callbacks=callbacks,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
        )

        records = [{"id": 1}, {"id": 2}]
        result = await executor.process(records)

        assert result.bronze_count == 2
        assert result.silver_count == 2
        assert (
            executor.records_fetched == 0
        )  # process() doesn't increment fetch counter
