"""Unit tests for BatchTransformer."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import bioetl.application.core.batch_transformer as batch_transformer_module
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.config import RecordProcessorConfig
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
    manager.quarantine_records = AsyncMock()
    manager.quarantine_filtered_record = AsyncMock()
    manager.quarantine_filtered_records = AsyncMock()
    return manager


@pytest.fixture
def mock_batch_metrics():
    """Create mock batch metrics recorder."""
    metrics = MagicMock(spec=BatchMetricsRecorder)
    return metrics


@pytest.fixture
def transform_callback():
    """Create mock transform callback."""

    async def transform(ctx, record, index):
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

    async def test_transform_batch_cooperatively_yields_to_event_loop(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
        monkeypatch,
    ) -> None:
        """Long-running transform loops should yield so heartbeat tasks can run."""
        marker_event = asyncio.Event()
        saw_background_progress = False

        async def marker() -> None:
            await asyncio.sleep(0)
            marker_event.set()

        async def blocking_transform(ctx, record, index):
            nonlocal saw_background_progress
            if index > 0 and marker_event.is_set():
                saw_background_progress = True
            deadline = time.perf_counter() + 0.003
            while time.perf_counter() < deadline:
                pass
            return {"entity_id": record.get("id"), "value": record.get("value")}

        monkeypatch.setattr(
            batch_transformer_module,
            "_YIELD_INTERVAL_SECONDS",
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

        await transformer.transform_batch(
            [{"id": str(i), "value": i} for i in range(12)],
            BatchID(uuid4()),
        )
        await marker_task

        assert saw_background_progress is True

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

        async def failing_transform(ctx, record, index):
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
        mock_quarantine_manager.quarantine_records.assert_called_once()

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

        async def failing_transform(ctx, record, index):
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

    async def test_transform_batch_quasi_quarantines_filtered_out(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that filter exclusions are captured in quasi-quarantine."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            if record.get("id") == "filtered":
                raise FilteredOutError("Record excluded by silver filters")
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
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "filtered", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 1
        assert result.quarantined_count == 0
        assert result.filtered_out_count == 1
        mock_quarantine_manager.quarantine_filtered_records.assert_called_once()

    async def test_transform_batch_continues_when_bulk_filtered_quarantine_fails(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Bulk quarantine failure should not fail batch transformation."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            raise FilteredOutError("Record excluded by silver filters")

        mock_quarantine_manager.quarantine_filtered_records.side_effect = RuntimeError(
            "disk full"
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
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "filtered", "value": 5}],
            BatchID(uuid4()),
        )

        assert result.filtered_out_count == 1
        assert result.records_quarantine_failed == 1
        mock_context.logger.error.assert_called()


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

        async def failing_transform(ctx, record, index):
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

        async def failing_transform(ctx, record, index):
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

        async def transform(ctx, record, index):
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
