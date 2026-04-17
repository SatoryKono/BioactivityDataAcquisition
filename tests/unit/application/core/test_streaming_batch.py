"""Unit tests for streaming batch processing."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import (
    BatchTransformer,
    StreamingBatchProcessor,
    TransformedRecord,
)
from bioetl.application.core.transformer_runtime import (
    orchestration as batch_transformer_orchestration,
)
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.domain.config import MemoryConfig
from bioetl.infrastructure.system.memory_monitor import MemoryMonitor
from bioetl.application.core.quarantine_manager import QuarantineManagerService
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError
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
    manager = MagicMock(spec=QuarantineManagerService)
    manager.quarantine_record = AsyncMock()
    manager.quarantine_records = AsyncMock()
    manager.quarantine_filtered_record = AsyncMock()
    manager.quarantine_filtered_records = AsyncMock()
    return manager


@pytest.fixture
def mock_batch_metrics():
    """Create mock batch metrics recorder."""
    return MagicMock(spec=BatchMetricsRecorder)


@pytest.fixture
def transform_callback():
    """Create transform callback."""

    async def transform(ctx, record, index):
        await asyncio.sleep(0)
        return {"entity_id": record.get("id", "unknown"), "value": record.get("value")}

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def gold_transform_callback():
    """Create gold transform callback."""

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
class TestTransformSingle:
    """Tests for BatchTransformer.transform_single method."""

    async def test_transform_single_success(self, batch_transformer):
        """Test successful single record transformation."""
        record = {"id": "1", "value": 10}
        batch_id = BatchID(uuid4())

        result = await batch_transformer.transform_single(record, batch_id)

        assert isinstance(result, TransformedRecord)
        assert result.silver_record is not None
        assert result.silver_record["entity_id"] == "1"
        assert result.gold_record is not None  # value > 5
        assert result.is_quarantined is False

    async def test_transform_single_filtered_from_gold(self, batch_transformer):
        """Test record that passes silver but not gold filter."""
        record = {"id": "2", "value": 3}  # value <= 5
        batch_id = BatchID(uuid4())

        result = await batch_transformer.transform_single(record, batch_id)

        assert result.silver_record is not None
        assert result.gold_record is None  # Filtered out
        assert result.is_quarantined is False

    async def test_transform_single_quarantine(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test quarantine on DQ error."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise DataQualityError("Invalid data")

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

        record = {"id": "bad", "value": 10}
        batch_id = BatchID(uuid4())

        result = await transformer.transform_single(record, batch_id)

        assert result.silver_record is None
        assert result.gold_record is None
        assert result.is_quarantined is True
        mock_quarantine_manager.quarantine_records.assert_called_once()
        assert (
            mock_quarantine_manager.quarantine_records.call_args.kwargs["run_id"]
            == mock_context.run_id
        )

    async def test_transform_single_filtered_out_quarantine_sink(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test filtered-out record is routed to quarantine storage."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise FilteredOutError(
                "Record excluded by silver filters",
                details={
                    "reason_code": "required_field_missing",
                    "rule_type": "required_fields",
                    "field": "publication_year",
                },
            )

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
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_single({"id": "f"}, BatchID(uuid4()))

        assert result.silver_record is None
        assert result.gold_record is None
        assert result.is_quarantined is False
        assert result.is_filtered_out is True
        mock_quarantine_manager.quarantine_filtered_records.assert_called_once()
        assert (
            mock_quarantine_manager.quarantine_filtered_records.call_args.kwargs[
                "run_id"
            ]
            == mock_context.run_id
        )
        mock_batch_metrics.track_silver_filter_rejection.assert_called_once_with(
            {
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "publication_year",
            }
        )


@pytest.mark.unit
class TestTransformStream:
    """Tests for BatchTransformer.transform_stream method."""

    async def test_transform_stream_processes_all_records(self, batch_transformer):
        """Test streaming transformation processes all records."""
        records = [
            {"id": "1", "value": 10},
            {"id": "2", "value": 3},
            {"id": "3", "value": 8},
        ]
        batch_id = BatchID(uuid4())

        result = await batch_transformer.transform_stream(records, batch_id)

        assert len(result.silver_records) == 3
        assert len(result.gold_records) == 2  # value > 5: records 1 and 3
        assert result.quarantined_count == 0

    async def test_transform_stream_cooperatively_yields_to_event_loop(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
        monkeypatch,
    ) -> None:
        """Streaming transform should yield during CPU-heavy record processing."""
        marker_event = asyncio.Event()
        saw_background_progress = False

        async def marker() -> None:
            await asyncio.sleep(0)
            marker_event.set()

        async def blocking_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal saw_background_progress
            if index > 0 and marker_event.is_set():
                saw_background_progress = True
            deadline = time.perf_counter() + 0.003
            while time.perf_counter() < deadline:
                pass
            return {"entity_id": record.get("id"), "value": record.get("value")}

        monkeypatch.setattr(
            batch_transformer_orchestration,
            "YIELD_INTERVAL_SECONDS",
            0.001,
        )
        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=blocking_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )
        marker_task = asyncio.create_task(marker())

        await transformer.transform_stream(
            [{"id": str(i), "value": i} for i in range(12)],
            BatchID(uuid4()),
        )
        await marker_task

        assert saw_background_progress is True

    async def test_transform_stream_handles_errors(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test streaming handles errors correctly."""

        async def selective_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid")
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
            transform_callback=selective_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good1", "value": 10},
            {"id": "bad", "value": 5},
            {"id": "good2", "value": 8},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_stream(records, batch_id)

        assert len(result.silver_records) == 2
        assert result.quarantined_count == 1
        assert (
            mock_quarantine_manager.quarantine_records.call_args.kwargs["run_id"]
            == mock_context.run_id
        )

    async def test_transform_stream_tracks_filtered_out(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test streaming transformation tracks filtered-out records separately."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def selective_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "filtered":
                raise FilteredOutError(
                    "Record excluded by silver filters",
                    details={
                        "reason_code": "required_field_missing",
                        "rule_type": "required_fields",
                        "field": "publication_year",
                    },
                )
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
            transform_callback=selective_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "filtered", "value": 8},
            {"id": "good2", "value": 7},
        ]

        result = await transformer.transform_stream(records, BatchID(uuid4()))

        assert len(result.silver_records) == 2
        assert len(result.gold_records) == 2
        assert result.quarantined_count == 0
        assert result.filtered_out_count == 1
        mock_quarantine_manager.quarantine_filtered_records.assert_called_once()
        assert (
            mock_quarantine_manager.quarantine_filtered_records.call_args.kwargs[
                "run_id"
            ]
            == mock_context.run_id
        )
        mock_batch_metrics.track_silver_filter_rejection.assert_called_once_with(
            {
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "publication_year",
            }
        )


@pytest.mark.unit
class TestStreamingBatchProcessor:
    """Tests for StreamingBatchProcessor class."""

    @pytest.fixture
    def mock_memory_monitor(self):
        """Create mock memory monitor."""
        monitor = MagicMock(spec=MemoryMonitor)
        monitor.get_recommended_batch_size = MagicMock(side_effect=lambda x: x)
        return monitor

    async def test_process_in_chunks_yields_results(
        self, batch_transformer, mock_memory_monitor
    ):
        """Test chunk processing yields TransformResult for each chunk."""
        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=mock_memory_monitor,
        )

        records = [{"id": str(i), "value": i} for i in range(10)]
        batch_id = BatchID(uuid4())

        chunks = []
        async for chunk in processor.process_in_chunks(records, batch_id, chunk_size=3):
            chunks.append(chunk)

        # Should have 4 chunks: 3 + 3 + 3 + 1
        assert len(chunks) == 4
        assert sum(len(c.silver_records) for c in chunks) == 10

    async def test_process_in_chunks_adapts_size(self, batch_transformer):
        """Test chunk size adapts under memory pressure."""

        # Monitor returns constant size to ensure predictable chunking
        monitor = MagicMock(spec=MemoryMonitor)
        monitor.get_recommended_batch_size = MagicMock(return_value=5)

        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=monitor,
        )

        records = [{"id": str(i), "value": i} for i in range(20)]
        batch_id = BatchID(uuid4())

        chunk_sizes = []
        async for chunk in processor.process_in_chunks(
            records, batch_id, chunk_size=10
        ):
            chunk_sizes.append(len(chunk.silver_records))

        # Should process all records in smaller chunks of 5
        # 20 records / 5 per chunk = 4 chunks
        assert len(chunk_sizes) == 4
        assert all(size == 5 for size in chunk_sizes)
        assert sum(chunk_sizes) == 20

    async def test_process_in_chunks_without_monitor(self, batch_transformer):
        """Test processing works without memory monitor."""
        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=None,
        )

        records = [{"id": str(i), "value": i * 2} for i in range(5)]
        batch_id = BatchID(uuid4())

        chunks = []
        async for chunk in processor.process_in_chunks(records, batch_id, chunk_size=2):
            chunks.append(chunk)

        assert len(chunks) == 3  # 2 + 2 + 1
        assert sum(len(c.silver_records) for c in chunks) == 5

    def test_iter_records_generator(self, batch_transformer):
        """Test iter_records yields records one at a time."""
        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=None,
        )

        records = [{"id": str(i)} for i in range(5)]

        yielded = list(processor.iter_records(records))

        assert len(yielded) == 5
        assert yielded == records


@pytest.mark.unit
class TestIntegration:
    """Integration tests for streaming batch processing."""

    @pytest.fixture
    def memory_config(self):
        """Create memory config for testing."""
        return MemoryConfig(
            max_batch_memory_mb=256,
            memory_pressure_threshold=0.8,
            min_batch_size=5,
            check_interval_records=10,
            enable_adaptive_sizing=True,
        )

    async def test_large_batch_processing(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
    ):
        """Test processing a larger batch efficiently."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {"entity_id": record["id"], "value": record["value"]}

        def gold_filter(ctx, record):
            return record["value"] > 50

        def gold_transform(ctx, record):
            return record

        config = RecordProcessorConfig(
            pipeline_name="test_large",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=gold_transform,
        )

        # Create 1000 records
        records = [{"id": str(i), "value": i % 100} for i in range(1000)]
        batch_id = BatchID(uuid4())

        # Process in chunks
        processor = StreamingBatchProcessor(transformer=transformer)

        total_silver = 0
        total_gold = 0
        chunk_count = 0

        async for chunk in processor.process_in_chunks(
            records, batch_id, chunk_size=100
        ):
            total_silver += len(chunk.silver_records)
            total_gold += len(chunk.gold_records)
            chunk_count += 1

        assert total_silver == 1000
        assert total_gold == 490  # Values 51-99 for each 100 = 49 * 10 = 490
        assert chunk_count == 10
