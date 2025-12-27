"""Unit tests for BatchWriter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import BatchID, RunType, ValidationResult


@pytest.fixture
def mock_storage():
    """Create mock storage."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


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
def mock_gold_validator():
    """Create mock gold validator."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def mock_error_classifier():
    """Create error classifier."""
    return ErrorClassifier()


@pytest.fixture
def mock_batch_metrics():
    """Create mock batch metrics recorder."""
    return MagicMock(spec=BatchMetricsRecorder)


@pytest.fixture
def batch_writer(
    mock_storage,
    mock_context,
    mock_gold_validator,
    mock_error_classifier,
    mock_batch_metrics,
):
    """Create BatchWriter instance."""
    config = RecordProcessorConfig(
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=MagicMock(),
        table_config=TableConfig(),
    )
    return BatchWriter(
        storage=mock_storage,
        context=mock_context,
        config=config,
        gold_validator=mock_gold_validator,
        error_classifier=mock_error_classifier,
        batch_metrics=mock_batch_metrics,
    )


@pytest.mark.unit
class TestBatchWriterBronze:
    """Tests for BatchWriter.write_bronze method."""

    async def test_write_bronze_serializes_to_json(self, batch_writer, mock_storage):
        """Test that records are serialized to JSON."""
        records = [{"id": "1", "value": 10}, {"id": "2", "value": 20}]
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime.now(UTC)

        await batch_writer.write_bronze(records, batch_id, ingestion_ts)

        mock_storage.write_bronze.assert_called_once()
        call_kwargs = mock_storage.write_bronze.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["entity"] == "test_entity"
        assert call_kwargs["batch_id"] == batch_id

    async def test_write_bronze_propagates_run_id(
        self, batch_writer, mock_storage, mock_context
    ):
        """Test that run_id is passed to storage."""
        records = [{"id": "1", "value": 10}]
        batch_id = BatchID(uuid4())
        ingestion_ts = mock_context.started_at

        await batch_writer.write_bronze(records, batch_id, ingestion_ts)

        call_kwargs = mock_storage.write_bronze.call_args[1]
        assert call_kwargs["run_id"] == mock_context.run_id
        assert call_kwargs["run_type"] == mock_context.run_type

    async def test_write_bronze_deterministic_ordering(
        self, batch_writer, mock_storage
    ):
        """Test that records are sorted for deterministic output."""
        # Records in reverse order
        records = [{"z": "last", "a": "first"}, {"a": "first", "z": "last"}]
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime.now(UTC)

        await batch_writer.write_bronze(records, batch_id, ingestion_ts)

        mock_storage.write_bronze.assert_called_once()


@pytest.mark.unit
class TestBatchWriterSilver:
    """Tests for BatchWriter.write_silver method."""

    async def test_write_silver_adds_metadata(
        self, batch_writer, mock_storage, mock_context
    ):
        """Test that Silver records get _source_batch_id from BatchWriter.

        Note: _run_id, _run_type, _ingestion_ts are added by the transformer
        (BaseTransformer.entity_to_silver_record), not by BatchWriter.
        BatchWriter only adds/updates _source_batch_id.
        """
        # Records already have lineage fields from transformer
        records = [
            {
                "entity_id": "1",
                "value": 10,
                "_run_id": str(mock_context.run_id),
                "_run_type": mock_context.run_type.value,
                "_ingestion_ts": mock_context.started_at.isoformat(),
            }
        ]
        batch_id = BatchID(uuid4())
        ingestion_ts = mock_context.started_at

        await batch_writer.write_silver(records, batch_id, ingestion_ts)

        call_kwargs = mock_storage.write_silver.call_args[1]
        silver_records = call_kwargs["records"]
        assert len(silver_records) == 1
        assert silver_records[0]["_run_id"] == str(mock_context.run_id)
        assert silver_records[0]["_run_type"] == mock_context.run_type.value
        assert silver_records[0]["_source_batch_id"] == str(batch_id)
        assert "_ingestion_ts" in silver_records[0]

    async def test_write_silver_uses_table_config(self, mock_storage, mock_context):
        """Test that table configuration is applied."""
        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            table_config=TableConfig(
                silver_table="custom_silver_table",
                primary_keys=["entity_id"],
            ),
        )

        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(
                validate=MagicMock(return_value=ValidationResult(valid=True))
            ),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        records = [{"entity_id": "1", "value": 10}]
        batch_id = BatchID(uuid4())

        await writer.write_silver(records, batch_id, mock_context.started_at)

        call_kwargs = mock_storage.write_silver.call_args[1]
        assert call_kwargs["table_name"] == "custom_silver_table"
        assert list(call_kwargs["primary_keys"]) == ["entity_id"]


@pytest.mark.unit
class TestBatchWriterGold:
    """Tests for BatchWriter.write_gold method."""

    async def test_write_gold_validates_records(
        self, batch_writer, mock_storage, mock_gold_validator
    ):
        """Test that Gold records are validated."""
        records = [{"entity_id": "1", "value": 10}]

        await batch_writer.write_gold(records)

        mock_gold_validator.validate.assert_called_once()
        mock_storage.write_gold.assert_called_once()

    async def test_write_gold_raises_on_validation_failure(
        self, mock_storage, mock_context
    ):
        """Test that validation failure raises SchemaViolationError."""
        failing_validator = MagicMock()
        failing_validator.validate = MagicMock(
            return_value=ValidationResult(valid=False, errors=["field_error"])
        )

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=failing_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        records = [{"entity_id": "1", "value": "invalid"}]

        with pytest.raises(SchemaViolationError):
            await writer.write_gold(records)

        mock_storage.write_gold.assert_not_called()

    async def test_write_gold_filters_to_schema_columns(
        self, mock_storage, mock_context
    ):
        """Test that records are filtered to schema columns."""

        class MockSchema:
            @staticmethod
            def to_schema():
                schema = MagicMock()
                schema.columns = {"entity_id": MagicMock(), "value": MagicMock()}
                return schema

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MockSchema,
        )

        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(
                validate=MagicMock(return_value=ValidationResult(valid=True))
            ),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        records = [{"entity_id": "1", "value": 10, "extra_field": "should_be_removed"}]

        await writer.write_gold(records)

        call_kwargs = mock_storage.write_gold.call_args[1]
        gold_records = call_kwargs["records"]
        assert "extra_field" not in gold_records[0]
        assert "entity_id" in gold_records[0]
        assert "value" in gold_records[0]


@pytest.mark.unit
class TestBatchWriterErrorLogging:
    """Tests for error logging functionality."""

    def test_log_and_track_write_error(
        self, batch_writer, mock_context, mock_batch_metrics
    ):
        """Test that errors are logged and tracked."""
        batch_id = BatchID(uuid4())
        error = ValueError("Test error")

        batch_writer.log_and_track_write_error("silver", error, batch_id)

        mock_context.logger.error.assert_called_once()
        mock_batch_metrics.track_error.assert_called_once()


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
def batch_writer_with_tracer(
    mock_storage,
    mock_context,
    mock_gold_validator,
    mock_error_classifier,
    mock_batch_metrics,
    mock_tracer,
):
    """Create BatchWriter instance with tracer."""
    config = RecordProcessorConfig(
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=MagicMock(),
        table_config=TableConfig(),
    )
    return BatchWriter(
        storage=mock_storage,
        context=mock_context,
        config=config,
        gold_validator=mock_gold_validator,
        error_classifier=mock_error_classifier,
        batch_metrics=mock_batch_metrics,
        tracer=mock_tracer,
    )


@pytest.mark.unit
class TestBatchWriterTracing:
    """Tests for BatchWriter tracing spans."""

    async def test_write_bronze_creates_span(
        self, batch_writer_with_tracer, mock_tracer, mock_storage
    ):
        """Test that write_bronze creates a tracing span."""
        records = [{"id": "1", "value": 10}]
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime.now(UTC)

        await batch_writer_with_tracer.write_bronze(records, batch_id, ingestion_ts)

        mock_tracer.get_tracer.assert_called_with("bioetl.batch_writer")
        inner_tracer = mock_tracer.get_tracer.return_value
        inner_tracer.start_as_current_span.assert_called_once()

        call_args = inner_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "write_bronze"
        attrs = call_args[1]["attributes"]
        assert attrs["bioetl.layer"] == "bronze"
        assert attrs["bioetl.record_count"] == 1
        assert attrs["bioetl.batch_id"] == str(batch_id)

    async def test_write_silver_creates_span(
        self, batch_writer_with_tracer, mock_tracer, mock_storage, mock_context
    ):
        """Test that write_silver creates a tracing span."""
        records = [{"entity_id": "1", "value": 10}]
        batch_id = BatchID(uuid4())
        ingestion_ts = mock_context.started_at

        await batch_writer_with_tracer.write_silver(records, batch_id, ingestion_ts)

        mock_tracer.get_tracer.assert_called_with("bioetl.batch_writer")
        inner_tracer = mock_tracer.get_tracer.return_value
        inner_tracer.start_as_current_span.assert_called_once()

        call_args = inner_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "write_silver"
        attrs = call_args[1]["attributes"]
        assert attrs["bioetl.layer"] == "silver"
        assert attrs["bioetl.record_count"] == 1

    async def test_write_gold_creates_span(
        self, batch_writer_with_tracer, mock_tracer, mock_storage, mock_gold_validator
    ):
        """Test that write_gold creates a tracing span."""
        records = [{"entity_id": "1", "value": 10}]

        await batch_writer_with_tracer.write_gold(records)

        mock_tracer.get_tracer.assert_called_with("bioetl.batch_writer")
        inner_tracer = mock_tracer.get_tracer.return_value
        inner_tracer.start_as_current_span.assert_called_once()

        call_args = inner_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "write_gold"
        attrs = call_args[1]["attributes"]
        assert attrs["bioetl.layer"] == "gold"
        assert attrs["bioetl.record_count"] == 1

    async def test_span_records_exception_on_error(
        self, mock_storage, mock_context, mock_tracer
    ):
        """Test that span records exception when write fails."""
        mock_storage.write_bronze = AsyncMock(side_effect=RuntimeError("Storage error"))

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            table_config=TableConfig(),
        )

        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            tracer=mock_tracer,
        )

        records = [{"id": "1"}]
        batch_id = BatchID(uuid4())

        with pytest.raises(RuntimeError):
            await writer.write_bronze(records, batch_id, datetime.now(UTC))

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.set_attribute.assert_called_with("error", True)
        span.record_exception.assert_called_once()

    async def test_no_span_without_tracer(self, batch_writer, mock_storage):
        """Test that no span is created when tracer is None."""
        records = [{"id": "1", "value": 10}]
        batch_id = BatchID(uuid4())
        ingestion_ts = datetime.now(UTC)

        # batch_writer fixture doesn't have tracer, should work without errors
        await batch_writer.write_bronze(records, batch_id, ingestion_ts)

        mock_storage.write_bronze.assert_called_once()
