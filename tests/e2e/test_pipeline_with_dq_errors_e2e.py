"""E2E tests for pipeline behavior with Data Quality errors.

Tests the pipeline's handling of DQ errors at various thresholds:
- Soft threshold (>5%): Warning logged but pipeline continues
- Hard threshold (>20%): Pipeline fails with DataQualityThresholdError

Per RULES.md §4.2:
- Soft threshold: >5% DQ errors → Warning
- Hard threshold: >20% DQ errors → Fail Batch
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.config import DQConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from collections.abc import Callable


class ForcedDQError(DataQualityError):
    """Test-specific DQ error for simulating failures."""

    def __init__(self, record_id: str) -> None:
        super().__init__(f"Forced DQ error for record {record_id}")


@pytest.fixture
def strict_dq_config() -> DQConfig:
    """Create a DQ config with strict thresholds for testing."""
    return DQConfig(
        soft_fail_threshold=0.05,  # 5%
        hard_fail_threshold=0.20,  # 20%
    )


@pytest.fixture
def lenient_dq_config() -> DQConfig:
    """Create a lenient DQ config that won't trigger warnings."""
    return DQConfig(
        soft_fail_threshold=0.50,  # 50%
        hard_fail_threshold=0.90,  # 90%
    )


def create_mock_transform_callback(
    error_rate: float,
) -> Callable[[PipelineContext, dict[str, Any]], dict[str, Any] | None]:
    """Create a transform callback that fails at specified rate.

    Args:
        error_rate: Fraction of records that should fail (0.0 to 1.0)

    Returns:
        Async transform callback function
    """
    call_count = 0

    async def transform(ctx: PipelineContext, record: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0)
        nonlocal call_count
        call_count += 1

        # Fail records based on error_rate
        if (call_count % 100) / 100.0 < error_rate:
            raise ForcedDQError(record.get("id", str(call_count)))

        return {
            "entity_id": record.get("id", f"entity_{call_count}"),
            "value": record.get("value", 0),
            "_run_id": str(uuid4()),
            "_run_type": "incremental",
            "_source_batch_id": str(uuid4()),
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        }

    return transform


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDQSoftThreshold:
    """Tests for DQ soft threshold (warning) behavior."""

    async def test_soft_threshold_logs_warning_but_continues(self, e2e_data_dir: Path):
        """E2E: Pipeline logs warning when DQ errors exceed soft threshold.

        When error rate is between soft and hard thresholds (5-20%),
        the pipeline should log a warning but continue processing.
        """
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        # Create mock context with warning tracking
        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)
        mock_logger.warning = MagicMock()

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Create config with strict DQ thresholds
        config = RecordProcessorConfig(
            pipeline_name="test_dq_soft",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )

        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)
        quarantine_manager.quarantine_record = AsyncMock()
        quarantine_manager.quarantine_filtered_record = AsyncMock()

        # Create transformer with 10% error rate (above soft, below hard)
        error_count = 0

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal error_count
            error_count += 1
            if error_count <= 10:  # First 10 of 100 records fail = 10%
                raise ForcedDQError(str(error_count))
            return {
                "entity_id": f"entity_{error_count}",
                "value": 1,
            }

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=failing_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        # Create 100 records
        records = [{"id": str(i), "value": i} for i in range(100)]
        batch_id = BatchID(uuid4())

        # Act
        result = await transformer.transform_batch(records, batch_id)

        # Assert - warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "DQ Soft Threshold" in str(call)
        ]
        assert len(warning_calls) >= 1, "Expected DQ Soft Threshold warning"

        # Assert - records were still processed
        assert len(result.silver_records) == 90  # 100 - 10 errors
        assert result.quarantined_count == 10

    async def test_below_soft_threshold_no_warning(self, e2e_data_dir: Path):
        """E2E: Pipeline does not warn when error rate is below soft threshold."""
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)
        mock_logger.warning = MagicMock()

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        config = RecordProcessorConfig(
            pipeline_name="test_dq_below_soft",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )

        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)
        quarantine_manager.quarantine_record = AsyncMock()
        quarantine_manager.quarantine_filtered_record = AsyncMock()

        # Only 2% error rate (below soft threshold)
        error_count = 0

        async def low_error_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal error_count
            error_count += 1
            if error_count <= 2:  # 2 of 100 = 2%
                raise ForcedDQError(str(error_count))
            return {"entity_id": f"entity_{error_count}", "value": 1}

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=low_error_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        records = [{"id": str(i)} for i in range(100)]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        # Assert - no DQ threshold warning
        dq_warnings = [
            call
            for call in mock_logger.warning.call_args_list
            if "DQ" in str(call) and "Threshold" in str(call)
        ]
        assert len(dq_warnings) == 0, "Should not warn below soft threshold"

        assert len(result.silver_records) == 98
        assert result.quarantined_count == 2


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDQHardThreshold:
    """Tests for DQ hard threshold (failure) behavior."""

    async def test_hard_threshold_raises_error(self, e2e_data_dir: Path):
        """E2E: Pipeline fails when DQ errors exceed hard threshold.

        When error rate exceeds 20%, the pipeline should raise
        DataQualityThresholdError and stop processing.
        """
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        config = RecordProcessorConfig(
            pipeline_name="test_dq_hard",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )

        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)
        quarantine_manager.quarantine_record = AsyncMock()
        quarantine_manager.quarantine_filtered_record = AsyncMock()

        # 25% error rate (above hard threshold)
        error_count = 0

        async def high_error_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal error_count
            error_count += 1
            if error_count <= 25:  # 25 of 100 = 25%
                raise ForcedDQError(str(error_count))
            return {"entity_id": f"entity_{error_count}", "value": 1}

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=high_error_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        records = [{"id": str(i)} for i in range(100)]
        batch_id = BatchID(uuid4())

        # Act & Assert
        with pytest.raises(DataQualityThresholdError) as exc_info:
            await transformer.transform_batch(records, batch_id)

        assert exc_info.value.error_rate == pytest.approx(0.25)
        assert exc_info.value.threshold == pytest.approx(0.20)

    async def test_hard_threshold_exactly_at_limit(self, e2e_data_dir: Path):
        """E2E: Pipeline fails when error rate equals hard threshold exactly."""
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        config = RecordProcessorConfig(
            pipeline_name="test_dq_exact",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )

        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)
        quarantine_manager.quarantine_record = AsyncMock()
        quarantine_manager.quarantine_filtered_record = AsyncMock()

        # Exactly 20% error rate
        error_count = 0

        async def exact_threshold_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal error_count
            error_count += 1
            if error_count <= 20:  # 20 of 100 = exactly 20%
                raise ForcedDQError(str(error_count))
            return {"entity_id": f"entity_{error_count}", "value": 1}

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=exact_threshold_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        records = [{"id": str(i)} for i in range(100)]
        batch_id = BatchID(uuid4())

        # Exactly at threshold should fail (>= check)
        with pytest.raises(DataQualityThresholdError):
            await transformer.transform_batch(records, batch_id)

    async def test_just_below_hard_threshold_succeeds(self, e2e_data_dir: Path):
        """E2E: Pipeline continues when error rate is just below hard threshold."""
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        config = RecordProcessorConfig(
            pipeline_name="test_dq_below_hard",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )

        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)
        quarantine_manager.quarantine_record = AsyncMock()
        quarantine_manager.quarantine_filtered_record = AsyncMock()

        # 19% error rate (just below hard threshold)
        error_count = 0

        async def below_hard_transform(ctx, record, index):
            await asyncio.sleep(0)
            nonlocal error_count
            error_count += 1
            if error_count <= 19:  # 19 of 100 = 19%
                raise ForcedDQError(str(error_count))
            return {"entity_id": f"entity_{error_count}", "value": 1}

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=below_hard_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        records = [{"id": str(i)} for i in range(100)]
        batch_id = BatchID(uuid4())

        # Should succeed (with warning since above soft threshold)
        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 81  # 100 - 19
        assert result.quarantined_count == 19


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDQQuarantineBehavior:
    """Tests for quarantine behavior during DQ errors."""

    async def test_quarantined_records_not_in_silver(self, e2e_data_dir: Path):
        """E2E: Quarantined records should not appear in Silver output."""
        from bioetl.application.core.batch_metrics import BatchMetricsRecorder
        from bioetl.application.core.batch_transformer import BatchTransformer
        from bioetl.application.core.config import RecordProcessorConfig
        from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
        from bioetl.domain.error_classifier import ErrorClassifier
        from bioetl.domain.types import BatchID

        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        config = RecordProcessorConfig(
            pipeline_name="test_quarantine",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.50,
                hard_fail_threshold=0.90,
            ),
        )

        quarantined_records: list[dict] = []
        quarantine_manager = MagicMock(spec=QuarantineRuntimeService)

        async def capture_quarantine_records(records, batch_id, **kwargs):
            await asyncio.sleep(0)
            for record, _error_type, _error_msg in records:
                quarantined_records.append(record)

        quarantine_manager.quarantine_records = AsyncMock(
            side_effect=capture_quarantine_records
        )
        quarantine_manager.quarantine_filtered_records = AsyncMock()

        # Fail specific records
        failed_ids = {"2", "5", "7"}

        async def selective_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record["id"] in failed_ids:
                raise ForcedDQError(record["id"])
            return {"entity_id": f"entity_{record['id']}", "value": 1}

        transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=ErrorClassifier(),
            quarantine_manager=quarantine_manager,
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            transform_callback=selective_transform,
            gold_filter_callback=lambda ctx, rec: True,
            gold_transform_callback=lambda ctx, rec: rec,
        )

        records = [{"id": str(i)} for i in range(10)]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        # Verify counts
        assert len(result.silver_records) == 7
        assert result.quarantined_count == 3
        assert len(quarantined_records) == 3

        # Verify failed IDs are not in silver
        silver_ids = {r["entity_id"] for r in result.silver_records}
        for failed_id in failed_ids:
            assert f"entity_{failed_id}" not in silver_ids

        # Verify failed IDs are in quarantine
        quarantine_ids = {r["id"] for r in quarantined_records}
        assert quarantine_ids == failed_ids
