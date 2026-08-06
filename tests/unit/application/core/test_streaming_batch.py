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
"""Unit tests for streaming batch processing."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

import pytest

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
from bioetl.domain.ports.runtime import MemoryMonitorPort
from bioetl.domain.exceptions import DataQualityError

pytest_plugins = ("tests.unit.application.core.transformer_test_support",)


@pytest.mark.unit
class TestTransformSingle:
    """Tests for BatchTransformer.transform_single method."""

    async def test_transform_single_success(self, batch_transformer):
        """Test successful single record transformation."""
        record = {"id": "1", "value": 10}
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

        result = await batch_transformer.transform_single(record, batch_id)

        assert isinstance(result, TransformedRecord)
        assert result.silver_record is not None
        assert result.silver_record["entity_id"] == "1"
        assert result.gold_record is not None  # value > 5
        assert result.is_quarantined is False

    async def test_transform_single_filtered_from_gold(self, batch_transformer):
        """Test record that passes silver but not gold filter."""
        record = {"id": "2", "value": 3}  # value <= 5
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

        result = await batch_transformer.transform_single(record, batch_id)

        assert result.silver_record is not None
        assert result.gold_record is None
        assert result.is_quarantined is False
        assert result.gold_excluded_by_contract is True

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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

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

        result = await transformer.transform_single(
            {"id": "f"}, deterministic_batch_uuid_from_callsite("test_streaming_batch")
        )

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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

        result = await batch_transformer.transform_stream(records, batch_id)

        assert len(result.silver_records) == 3
        assert len(result.gold_records) == 2  # value > 5: records 1 and 3
        assert result.quarantined_count == 0
        assert result.gold_excluded_by_contract_count == 1

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
                continue
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
            deterministic_batch_uuid_from_callsite("test_streaming_batch"),
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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

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

        result = await transformer.transform_stream(
            records, deterministic_batch_uuid_from_callsite("test_streaming_batch")
        )

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
        monitor = MagicMock(spec=MemoryMonitorPort)
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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

        chunks = []
        async for chunk in processor.process_in_chunks(records, batch_id, chunk_size=3):
            chunks.append(chunk)

        # Should have 4 chunks: 3 + 3 + 3 + 1
        assert len(chunks) == 4
        assert sum(len(c.silver_records) for c in chunks) == 10

    async def test_process_in_chunks_rejects_zero_chunk_size(
        self, batch_transformer, mock_memory_monitor
    ):
        """chunk_size < 1 must fail closed before the streaming loop."""
        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=mock_memory_monitor,
        )
        records = [{"id": "1"}]
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch_zero")
        with pytest.raises(ValueError, match="chunk_size must be >= 1"):
            async for _ in processor.process_in_chunks(
                records, batch_id, chunk_size=0
            ):
                pass

    async def test_process_in_chunks_adapts_size(self, batch_transformer):
        """Test chunk size adapts under memory pressure."""

        # Monitor returns constant size to ensure predictable chunking
        monitor = MagicMock(spec=MemoryMonitorPort)
        monitor.get_recommended_batch_size = MagicMock(return_value=5)

        processor = StreamingBatchProcessor(
            transformer=batch_transformer,
            memory_monitor=monitor,
        )

        records = [{"id": str(i), "value": i} for i in range(20)]
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

        chunk_sizes = []
        async for chunk in processor.process_in_chunks(
            records, batch_id, chunk_size=10
        ):
            chunk_sizes.append(len(chunk.silver_records))

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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

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
        batch_id = deterministic_batch_uuid_from_callsite("test_streaming_batch")

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
        assert total_gold == 490
        assert chunk_count == 10
