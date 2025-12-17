"""Unit tests for RecordProcessor."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier, ErrorType
from bioetl.domain.exceptions import DataQualityError
from bioetl.domain.types import BatchID, RunID, RunType


@pytest.fixture
def mock_storage():
    """Create mock storage."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_quarantine_manager():
    """Create mock quarantine manager."""
    manager = MagicMock(spec=QuarantineManager)
    manager.quarantine_record = AsyncMock()
    return manager


@pytest.fixture
def mock_error_classifier():
    """Create mock error classifier."""
    return ErrorClassifier()


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
def transform_callback():
    """Create mock transform callback."""

    async def transform(ctx, record):
        return {"entity_id": record.get("id", "unknown"), "value": record.get("value")}

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create mock gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def record_processor(
    mock_storage,
    mock_quarantine_manager,
    mock_error_classifier,
    mock_context,
    transform_callback,
    gold_filter_callback,
):
    """Create RecordProcessor instance."""
    return RecordProcessor(
        storage=mock_storage,
        quarantine_manager=mock_quarantine_manager,
        error_classifier=mock_error_classifier,
        context=mock_context,
        provider="test_provider",
        entity_type="test_entity",
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
    )


@pytest.mark.unit
class TestRecordProcessorInit:
    """Tests for RecordProcessor initialization."""

    def test_init_stores_dependencies(self, record_processor, mock_storage):
        """Test that initialization stores all dependencies."""
        assert record_processor._storage is mock_storage


@pytest.mark.unit
class TestRecordProcessorProcessBatch:
    """Tests for process_batch method."""

    @pytest.mark.asyncio
    async def test_process_batch_writes_to_all_layers(
        self, record_processor, mock_storage
    ):
        """Test that process_batch writes to Bronze, Silver, and Gold."""
        records = [
            {"id": "1", "value": 10},  # Goes to gold (value > 5)
            {"id": "2", "value": 3},  # Not in gold
        ]
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert bronze == 2
        assert silver == 2
        assert gold == 1
        assert quarantined == 0
        mock_storage.write_bronze.assert_called_once()
        mock_storage.write_silver.assert_called_once()
        mock_storage.write_gold.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_batch_no_gold_records(self, record_processor, mock_storage):
        """Test process_batch when no records pass gold filter."""
        records = [
            {"id": "1", "value": 1},
            {"id": "2", "value": 2},
        ]
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert gold == 0
        mock_storage.write_gold.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_batch_handles_transform_error(
        self, mock_storage, mock_quarantine_manager, mock_error_classifier, mock_context
    ):
        """Test that transform errors result in quarantine."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor = RecordProcessor(
            storage=mock_storage,
            quarantine_manager=mock_quarantine_manager,
            error_classifier=mock_error_classifier,
            context=mock_context,
            provider="test",
            entity_type="test",
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},  # Will fail transform
        ]
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await processor.process_batch(
            records, batch_id
        )

        assert bronze == 2
        assert silver == 1
        assert quarantined == 1
        mock_quarantine_manager.quarantine_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_batch_raises_non_data_quality_errors(
        self, mock_storage, mock_quarantine_manager, mock_error_classifier, mock_context
    ):
        """Test that non-data-quality errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record):
            raise LockLostError("resource_key", "test_run_id")

        processor = RecordProcessor(
            storage=mock_storage,
            quarantine_manager=mock_quarantine_manager,
            error_classifier=mock_error_classifier,
            context=mock_context,
            provider="test",
            entity_type="test",
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
        )

        records = [{"id": "test", "value": 5}]
        batch_id = BatchID(uuid4())

        with pytest.raises(LockLostError):
            await processor.process_batch(records, batch_id)

    @pytest.mark.asyncio
    async def test_process_batch_empty_records(self, record_processor, mock_storage):
        """Test process_batch with empty records list."""
        records = []
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert bronze == 0
        assert silver == 0
        assert gold == 0
        mock_storage.write_silver.assert_not_called()
        mock_storage.write_gold.assert_not_called()
