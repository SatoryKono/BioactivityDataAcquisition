"""Unit tests for PipelineExecutor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import BatchResult, RecordProcessor
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.types import RunType


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.data_source = AsyncMock()
    services.logger = MagicMock()
    return services


@pytest.fixture
def mock_record_processor():
    """Create mock record processor."""
    processor = MagicMock(spec=RecordProcessor)
    processor.process_batch = AsyncMock(
        return_value=BatchResult(
            bronze_count=0, silver_count=0, gold_count=0, quarantined_count=0
        )
    )
    return processor


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
def executor(
    mock_services,
    mock_record_processor,
    mock_checkpoint_manager,
    shutdown_signal,
):
    """Create PipelineExecutor instance."""
    return PipelineExecutor(
        services=mock_services,
        record_processor=mock_record_processor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        entity_type="test_entity",
        batch_size=10,
        checkpoint_interval=5,
    )


@pytest.mark.unit
class TestPipelineExecutorInit:
    """Tests for PipelineExecutor initialization."""

    def test_init_stores_batch_size(self, executor):
        """Test that initialization stores batch size."""
        assert executor.batch_size == 10

    def test_init_stores_checkpoint_interval(self, executor):
        """Test that initialization stores checkpoint interval."""
        assert executor.checkpoint_interval == 5

    def test_init_default_batch_size(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test default batch size when not specified."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test",
        )
        assert executor.batch_size == PipelineExecutor.DEFAULT_BATCH_SIZE

    def test_init_counters_zero(self, executor):
        """Test that counters start at zero."""
        assert executor.records_fetched == 0
        assert executor.records_bronze == 0
        assert executor.records_silver == 0
        assert executor.records_gold == 0
        assert executor.records_quarantined == 0


@pytest.mark.unit
class TestPipelineExecutorExecute:
    """Tests for execute method."""

    async def test_execute_processes_records(
        self, executor, mock_services, mock_record_processor
    ):
        """Test that execute processes records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch
        mock_record_processor.process_batch.return_value = BatchResult(
            bronze_count=3, silver_count=3, gold_count=3, quarantined_count=0
        )

        await executor.execute(limit=None)

        assert executor.records_fetched == 3
        assert executor.records_bronze == 3
        assert executor.records_silver == 3
        assert executor.records_gold == 3
        mock_record_processor.process_batch.assert_called()

    async def test_execute_batches_records(
        self, executor, mock_services, mock_record_processor
    ):
        """Test that execute batches records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(15):  # More than batch size of 10
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # Should have called process_batch twice (batch of 10 + batch of 5)
        assert mock_record_processor.process_batch.call_count == 2

    async def test_execute_checkpoints_at_interval(
        self, executor, mock_services, mock_checkpoint_manager
    ):
        """Test that execute checkpoints at configured interval."""

        async def mock_fetch(**kwargs):
            for i in range(10):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # With checkpoint_interval=5, should checkpoint at record 5 and 10
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2

    async def test_execute_handles_shutdown(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown saves checkpoint."""
        records_yielded = 0

        async def mock_fetch(**kwargs):
            nonlocal records_yielded
            for i in range(10):
                yield {"id": str(i), "value": 10}
                records_yielded += 1
                if records_yielded == 3:
                    # Trigger shutdown after 3 records
                    shutdown_signal.request()

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(limit=None)

        # Should have saved checkpoint before shutdown
        mock_checkpoint_manager.save_checkpoint.assert_called()

    async def test_execute_shutdown_early(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown at start of processing."""

        async def mock_fetch(**kwargs):
            shutdown_signal.request()
            yield {"id": "0", "value": 10}

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(limit=None)

    async def test_execute_empty_data(
        self, executor, mock_services, mock_record_processor
    ):
        """Test execute with no data."""

        async def mock_fetch(**kwargs):
            if False:  # Empty generator
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        assert executor.records_fetched == 0
        mock_record_processor.process_batch.assert_not_called()

    async def test_execute_passes_limit(self, executor, mock_services):
        """Test that limit is passed to data source."""
        captured_kwargs = {}

        async def mock_fetch(**kwargs):
            captured_kwargs.update(kwargs)
            if False:
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=100)

        assert captured_kwargs.get("limit") == 100


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
def executor_with_tracer(
    mock_services,
    mock_record_processor,
    mock_checkpoint_manager,
    shutdown_signal,
    mock_tracer,
):
    """Create PipelineExecutor instance with tracer."""
    run_id = str(uuid4())
    return PipelineExecutor(
        services=mock_services,
        record_processor=mock_record_processor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        entity_type="test_entity",
        batch_size=10,
        checkpoint_interval=5,
        run_type=RunType.INCREMENTAL,
        tracer=mock_tracer,
        pipeline_name="test_pipeline",
        run_id=run_id,
    )


@pytest.mark.unit
class TestPipelineExecutorTracing:
    """Tests for PipelineExecutor tracing spans."""

    async def test_execute_creates_root_span(
        self, executor_with_tracer, mock_services, mock_tracer
    ):
        """Test that execute creates a root span."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor_with_tracer.execute(limit=None)

        mock_tracer.get_tracer.assert_called_with("bioetl.executor")
        inner_tracer = mock_tracer.get_tracer.return_value
        inner_tracer.start_as_current_span.assert_called()

        # Check root span was created with correct name and attributes
        calls = inner_tracer.start_as_current_span.call_args_list
        root_span_call = calls[0]  # First call is the root span
        assert root_span_call[0][0] == "pipeline_execution"
        attrs = root_span_call[1]["attributes"]
        assert attrs["bioetl.pipeline"] == "test_pipeline"
        assert "bioetl.run_id" in attrs
        assert attrs["bioetl.entity_type"] == "test_entity"
        assert attrs["bioetl.run_type"] == "incremental"

    async def test_root_span_records_final_counts(
        self, executor_with_tracer, mock_services, mock_tracer, mock_record_processor
    ):
        """Test that root span records final record counts."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch
        mock_record_processor.process_batch.return_value = BatchResult(
            bronze_count=3, silver_count=3, gold_count=3, quarantined_count=0
        )

        await executor_with_tracer.execute(limit=None)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        # Verify set_attribute was called with count values
        set_attribute_calls = span.set_attribute.call_args_list
        attr_names = [call[0][0] for call in set_attribute_calls]
        assert "bioetl.total_fetched" in attr_names
        assert "bioetl.total_bronze" in attr_names
        assert "bioetl.total_silver" in attr_names
        assert "bioetl.total_gold" in attr_names

    async def test_root_span_records_exception_on_error(
        self, mock_services, mock_tracer, mock_checkpoint_manager, shutdown_signal
    ):
        """Test that root span records exception when execution fails."""
        mock_record_processor = MagicMock(spec=RecordProcessor)
        mock_record_processor.process_batch = AsyncMock(
            side_effect=RuntimeError("Processing error")
        )

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=10,
            tracer=mock_tracer,
            pipeline_name="test_pipeline",
            run_id=str(uuid4()),
        )

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(RuntimeError):
            await executor.execute(limit=None)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.set_attribute.assert_any_call("error", True)
        # Exception is recorded by both root span and batch span, so called at least once
        assert span.record_exception.called

    async def test_root_span_records_shutdown(
        self, executor_with_tracer, mock_services, mock_tracer, shutdown_signal
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
            await executor_with_tracer.execute(limit=None)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.set_attribute.assert_any_call("bioetl.shutdown", True)

    async def test_no_span_without_tracer(self, executor, mock_services):
        """Test that no span is created when tracer is None."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        # executor fixture doesn't have tracer, should work without errors
        await executor.execute(limit=None)
