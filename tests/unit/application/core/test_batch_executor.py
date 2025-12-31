"""Unit tests for BatchExecutor.

Tests the unified BatchExecutor that combines functionality from
PipelineExecutor and RecordProcessor.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_executor import BatchExecutor, BatchResult
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.config import TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.types import RunType, ValidationResult


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
    metrics = AsyncMock()
    return metrics


@pytest.fixture
def mock_quarantine_port():
    """Create mock quarantine port."""
    port = AsyncMock()
    port.write = AsyncMock()
    return port


@pytest.fixture
def mock_services(mock_storage, mock_metrics, mock_quarantine_port):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.storage = mock_storage
    services.metrics = mock_metrics
    services.quarantine = mock_quarantine_port
    services.data_source = AsyncMock()
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
def shutdown_signal():
    """Create shutdown signal."""
    return ShutdownSignal()


@pytest.fixture
def transform_callback():
    """Create mock transform callback with lineage fields."""

    async def transform(ctx, record, index):
        return {
            "entity_id": record.get("id", "unknown"),
            "value": record.get("value"),
            "_run_id": str(ctx.run_id),
            "_run_type": ctx.run_type.value,
            "_ingestion_ts": ctx.started_at.isoformat(),
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
        gold_schema=MagicMock(),
        table_config=TableConfig(),
    )


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
    return BatchExecutor(
        services=mock_services,
        context=mock_context,
        config=processor_config,
        error_classifier=ErrorClassifier(),
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
        executor = BatchExecutor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
        )
        assert executor.batch_size == BatchExecutor.DEFAULT_BATCH_SIZE

    def test_init_counters_zero(self, batch_executor):
        """Test that counters start at zero."""
        assert batch_executor.records_fetched == 0
        assert batch_executor.records_bronze == 0
        assert batch_executor.records_silver == 0
        assert batch_executor.records_gold == 0
        assert batch_executor.records_quarantined == 0

    def test_init_creates_internal_components(self, batch_executor):
        """Test that initialization creates BatchTransformer and BatchWriter."""
        assert batch_executor._transformer is not None
        assert batch_executor._writer is not None
        assert batch_executor._batch_metrics is not None


@pytest.mark.unit
class TestBatchExecutorExecute:
    """Tests for execute method."""

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
        assert batch_executor.records_gold == 3
        mock_storage.write_bronze.assert_called()
        mock_storage.write_silver.assert_called()
        mock_storage.write_gold.assert_called()

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
            if False:
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
            if False:
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await batch_executor.execute(limit=100)

        assert captured_kwargs.get("limit") == 100


@pytest.mark.unit
class TestBatchExecutorProcessBatch:
    """Tests for batch processing functionality."""

    async def test_process_batch_writes_to_all_layers(
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
        assert batch_executor.records_gold == 1
        assert batch_executor.records_quarantined == 0
        mock_storage.write_bronze.assert_called_once()
        mock_storage.write_silver.assert_called_once()
        mock_storage.write_gold.assert_called_once()

    async def test_process_batch_no_gold_records(
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

    async def test_process_batch_handles_transform_error(
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
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        executor = BatchExecutor(
            services=mock_services,
            context=mock_context,
            config=processor_config,
            error_classifier=ErrorClassifier(),
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
        assert executor.records_silver == 1
        assert executor.records_quarantined == 1
        mock_services.quarantine.write.assert_called_once()


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
    return BatchExecutor(
        services=mock_services,
        context=mock_context,
        config=processor_config,
        error_classifier=ErrorClassifier(),
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

    async def test_no_span_without_tracer(self, batch_executor, mock_services):
        """Test that no span is created when tracer is None."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        # batch_executor fixture doesn't have tracer, should work without errors
        await batch_executor.execute(limit=None)


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
        with pytest.raises(AttributeError):
            result.bronze_count = 20

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
