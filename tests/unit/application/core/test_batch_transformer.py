"""Unit tests for BatchTransformer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.memory_manager import MemoryConfig, MemoryManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.config import DQConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.types import BatchID, RunType


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
def mock_error_classifier():
    """Create error classifier."""
    return ErrorClassifier()


@pytest.fixture
def mock_quarantine_manager():
    """Create mock quarantine manager."""
    manager = MagicMock(spec=QuarantineManager)
    manager.quarantine_record = AsyncMock()
    return manager


@pytest.fixture
def mock_batch_metrics():
    """Create mock batch metrics recorder."""
    metrics = MagicMock(spec=BatchMetricsRecorder)
    return metrics


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
def gold_transform_callback():
    """Create mock gold transform callback."""

    def transform_gold(ctx, record):
        return record

    return transform_gold


@pytest.fixture
def batch_transformer(
    mock_context,
    mock_error_classifier,
    mock_quarantine_manager,
    mock_batch_metrics,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
):
    """Create BatchTransformer instance."""
    config = RecordProcessorConfig(
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=MagicMock(),
    )
    return BatchTransformer(
        context=mock_context,
        config=config,
        error_classifier=mock_error_classifier,
        quarantine_manager=mock_quarantine_manager,
        batch_metrics=mock_batch_metrics,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
    )


@pytest.mark.unit
class TestBatchTransformerTransform:
    """Tests for BatchTransformer.transform_batch method."""

    async def test_transform_batch_returns_silver_and_gold_records(
        self, batch_transformer
    ):
        """Test successful transformation returns correct records."""
        records = [
            {"id": "1", "value": 10},  # Goes to gold (value > 5)
            {"id": "2", "value": 3},  # Not in gold
        ]
        batch_id = BatchID(uuid4())

        result = await batch_transformer.transform_batch(records, batch_id)

        assert isinstance(result, TransformResult)
        assert len(result.silver_records) == 2
        assert len(result.gold_records) == 1
        assert result.quarantined_count == 0

    async def test_transform_batch_empty_records(self, batch_transformer):
        """Test transformation with empty records list."""
        result = await batch_transformer.transform_batch([], BatchID(uuid4()))

        assert result.silver_records == []
        assert result.gold_records == []
        assert result.quarantined_count == 0

    async def test_transform_batch_quarantines_dq_errors(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that data quality errors result in quarantine."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 1
        assert result.quarantined_count == 1
        mock_quarantine_manager.quarantine_record.assert_called_once()

    async def test_transform_batch_raises_non_dq_errors(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that non-DQ errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record):
            raise LockLostError("resource_key", "test_run_id")

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [{"id": "test", "value": 5}]
        batch_id = BatchID(uuid4())

        with pytest.raises(LockLostError):
            await transformer.transform_batch(records, batch_id)


@pytest.mark.unit
class TestBatchTransformerDQThresholds:
    """Tests for DQ threshold checking."""

    async def test_hard_threshold_exceeded_raises_error(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that exceeding hard threshold raises DataQualityThresholdError."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.4),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # 50% error rate (1/2) > hard_fail_threshold (0.4)
        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        with pytest.raises(DataQualityThresholdError):
            await transformer.transform_batch(records, batch_id)

    async def test_soft_threshold_logs_warning(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that exceeding soft threshold logs warning but doesn't raise."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.9),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # 50% error rate > soft_fail_threshold (0.1) but < hard_fail_threshold (0.9)
        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 1
        assert result.quarantined_count == 1
        mock_context.logger.warning.assert_called_once()

    async def test_below_thresholds_no_warning(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that below thresholds results in no warnings."""

        async def transform(ctx, record):
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.5, hard_fail_threshold=0.9),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [{"id": "1", "value": 10}, {"id": "2", "value": 5}]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 2
        assert result.quarantined_count == 0
        mock_context.logger.warning.assert_not_called()


@pytest.mark.unit
class TestBatchTransformerStreaming:
    """Tests for streaming transformation methods."""

    async def test_transform_batch_streaming_empty_records(self, batch_transformer):
        """Test streaming transformation with empty records."""
        batch_id = BatchID(uuid4())

        results = []
        async for result in batch_transformer.transform_batch_streaming(
            [], batch_id, chunk_size=10
        ):
            results.append(result)

        assert len(results) == 0

    async def test_transform_batch_streaming_single_chunk(self, batch_transformer):
        """Test streaming transformation that fits in one chunk."""
        records = [
            {"id": "1", "value": 10},
            {"id": "2", "value": 3},
        ]
        batch_id = BatchID(uuid4())

        results = []
        async for result in batch_transformer.transform_batch_streaming(
            records, batch_id, chunk_size=10
        ):
            results.append(result)

        assert len(results) == 1
        assert len(results[0].silver_records) == 2
        assert len(results[0].gold_records) == 1  # Only value > 5

    async def test_transform_batch_streaming_multiple_chunks(self, batch_transformer):
        """Test streaming transformation that spans multiple chunks."""
        records = [{"id": str(i), "value": 10} for i in range(25)]
        batch_id = BatchID(uuid4())

        results = []
        async for result in batch_transformer.transform_batch_streaming(
            records, batch_id, chunk_size=10
        ):
            results.append(result)

        # Should have 3 chunks: 10 + 10 + 5
        assert len(results) == 3
        assert len(results[0].silver_records) == 10
        assert len(results[1].silver_records) == 10
        assert len(results[2].silver_records) == 5

        # All records should pass gold filter (value > 5)
        total_gold = sum(len(r.gold_records) for r in results)
        assert total_gold == 25

    async def test_transform_batch_streaming_with_memory_manager(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test streaming with memory manager."""
        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # Create memory manager with disabled state
        memory_config = MemoryConfig(enabled=False)
        memory_manager = MemoryManager(config=memory_config)

        records = [{"id": str(i), "value": 10} for i in range(20)]
        batch_id = BatchID(uuid4())

        results = []
        async for result in transformer.transform_batch_streaming(
            records, batch_id, chunk_size=10, memory_manager=memory_manager
        ):
            results.append(result)

        # With disabled memory manager, should still process correctly
        assert len(results) == 2
        total_silver = sum(len(r.silver_records) for r in results)
        assert total_silver == 20

    async def test_transform_batch_streaming_aggregates_quarantine_count(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that quarantine count is tracked across chunks."""

        async def failing_transform(ctx, record):
            if int(record.get("id", 0)) % 2 == 0:
                raise DataQualityError("Even IDs fail")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [{"id": str(i), "value": 10} for i in range(10)]
        batch_id = BatchID(uuid4())

        total_quarantined = 0
        results = []
        async for result in transformer.transform_batch_streaming(
            records, batch_id, chunk_size=5
        ):
            results.append(result)
            total_quarantined += result.quarantined_count

        # 5 records quarantined (IDs 0, 2, 4, 6, 8)
        assert total_quarantined == 5


@pytest.mark.unit
class TestBatchTransformerIterChunks:
    """Tests for _iter_chunks helper method."""

    def test_iter_chunks_empty(self, batch_transformer):
        """Test chunking empty list."""
        chunks = list(batch_transformer._iter_chunks([], 10))
        assert chunks == []

    def test_iter_chunks_smaller_than_chunk_size(self, batch_transformer):
        """Test chunking list smaller than chunk size."""
        records = [{"id": str(i)} for i in range(5)]
        chunks = list(batch_transformer._iter_chunks(records, 10))

        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_iter_chunks_exact_multiple(self, batch_transformer):
        """Test chunking list that's exact multiple of chunk size."""
        records = [{"id": str(i)} for i in range(20)]
        chunks = list(batch_transformer._iter_chunks(records, 10))

        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10

    def test_iter_chunks_with_remainder(self, batch_transformer):
        """Test chunking list with remainder."""
        records = [{"id": str(i)} for i in range(25)]
        chunks = list(batch_transformer._iter_chunks(records, 10))

        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5
