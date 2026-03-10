"""Unit tests for BatchExecutor memory management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.config import MemoryConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import MemoryMonitorPort, MetricsPort
from bioetl.domain.types import RunType, ValidationResult


from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.batch_transformer import BatchTransformer
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManagerService


def create_batch_executor(
    *,
    services,
    context,
    config,
    error_classifier,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    gold_validator,
    checkpoint_manager,
    shutdown_signal,
    batch_size=None,
    checkpoint_interval=None,
    tracer=None,
    lock_validator=None,
    memory_monitor=None,
    memory_config=None,
):
    resolved_batch_size = (
        batch_size if batch_size is not None else BatchExecutor.DEFAULT_BATCH_SIZE
    )
    batch_metrics = BatchMetricsRecorderService(
        services.metrics,
        f"{config.provider}_{config.entity_type}",
        context.run_type.value,
    )
    transformer = BatchTransformer(
        context=context,
        config=config,
        error_classifier=error_classifier,
        quarantine_manager=QuarantineManagerService(
            quarantine_port=services.quarantine,
            pipeline_name=config.pipeline_name,
            metrics=services.metrics,
        ),
        batch_metrics=batch_metrics,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
    )
    writer = BatchWriter(
        storage=services.storage,
        context=context,
        config=config,
        gold_validator=gold_validator,
        error_classifier=error_classifier,
        batch_metrics=batch_metrics,
        tracer=tracer,
        lock_validator=lock_validator,
    )
    memory_manager = BatchMemoryManagerService(
        resolved_batch_size,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        logger=services.logger,
    )
    tracing_manager = BatchTracingManagerService(
        tracer=tracer,
        context=context,
        config=config,
        initial_batch_size=resolved_batch_size,
        adaptive_sizing_enabled=memory_manager.enabled,
    )
    return BatchExecutor(
        services=services,
        context=context,
        config=config,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=shutdown_signal,
        batch_metrics=batch_metrics,
        transformer=transformer,
        writer=writer,
        memory_manager=memory_manager,
        tracing_manager=tracing_manager,
        batch_size=batch_size,
        checkpoint_interval=checkpoint_interval,
    )


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
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
        run_id=uuid4(),
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
        gold_schema=MagicMock(),
        table_config=TableConfig(),
    )


@pytest.fixture
def callbacks():
    """Create mock callbacks."""

    async def transform(ctx, record, index):
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
        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
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

        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
            batch_size=100,
            memory_monitor=memory_monitor,
            memory_config=MemoryConfig(
                enable_adaptive_sizing=True, check_interval_records=1
            ),
        )

        # Mock fetch to yield records
        async def mock_fetch(**kwargs):
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

        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
            batch_size=100,
            memory_monitor=memory_monitor,
            memory_config=MemoryConfig(
                enable_adaptive_sizing=True, check_interval_records=1
            ),
        )

        async def mock_fetch(**kwargs):
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
        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
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

        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
            batch_size=10,
        )

        async def mock_fetch(**kwargs):
            yield {"id": 1, "value": "test"}

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

        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
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
        executor = create_batch_executor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=callbacks["transform"],
            gold_filter_callback=callbacks["gold_filter"],
            gold_transform_callback=callbacks["gold_transform"],
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=ShutdownSignal(),
        )

        records = [{"id": 1}, {"id": 2}]
        result = await executor.process(records)

        assert result.bronze_count == 2
        assert result.silver_count == 2
        assert (
            executor.records_fetched == 0
        )  # process() doesn't increment fetch counter
