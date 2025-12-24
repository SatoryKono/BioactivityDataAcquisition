"""Unit tests for RecordProcessor metrics recording."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier, ErrorType
from bioetl.domain.types import BatchID, RunType, ValidationResult


@pytest.fixture
def mock_metrics():
    """Create mock metrics."""
    metrics = AsyncMock()
    return metrics


@pytest.fixture
def mock_services(mock_metrics):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.storage = AsyncMock()
    services.metrics = mock_metrics
    services.quarantine = AsyncMock()
    return services


@pytest.fixture
def mock_error_classifier():
    """Create mock error classifier."""
    classifier = ErrorClassifier()
    # Mock classify to control error type
    classifier.classify = MagicMock()
    return classifier


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
def record_processor(
    mock_services,
    mock_error_classifier,
    mock_context,
    mock_gold_validator,
):
    """Create RecordProcessor instance with dummy callbacks."""
    config = RecordProcessorConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        silver_schema=MagicMock(),
    )
    return RecordProcessor(
        services=mock_services,
        error_classifier=mock_error_classifier,
        context=mock_context,
        config=config,
        transform_callback=AsyncMock(return_value={"id": 1}),
        gold_filter_callback=MagicMock(return_value=True),
        gold_transform_callback=MagicMock(side_effect=lambda c, r: r),
        gold_validator=mock_gold_validator,
    )


@pytest.mark.unit
class TestRecordProcessorMetrics:
    """Tests for RecordProcessor metrics logic."""

    async def test_process_batch_records_batch_size_and_counts(
        self, record_processor, mock_metrics, mock_context
    ):
        """Test that batch size histogram and counters are recorded with correct labels."""
        records = [{"id": 1}, {"id": 2}]
        batch_id = BatchID(uuid4())

        await record_processor.process_batch(records, batch_id)

        pipeline_label = "test_entity"  # "test_entity" since provider="test", entity="entity" -> "test_entity"
        run_type_label = mock_context.run_type.value

        # Verify batch size histogram
        mock_metrics.observe_histogram.assert_called_with(
            "batch_size_records",
            2,
            {"pipeline": pipeline_label, "stage": "bronze"},
        )

        # Verify counters
        # We expect calls for bronze, quarantined (0), silver (2), gold (2)
        # Using any_order=True or checking specific calls

        # Bronze count
        mock_metrics.increment_counter.assert_any_call(
            "records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "bronze", "run_type": run_type_label},
        )

        # Silver count
        mock_metrics.increment_counter.assert_any_call(
            "records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "silver", "run_type": run_type_label},
        )

        # Gold count
        mock_metrics.increment_counter.assert_any_call(
            "records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "gold", "run_type": run_type_label},
        )

    async def test_process_batch_records_quarantine_metrics(
        self, record_processor, mock_metrics, mock_context, mock_error_classifier
    ):
        """Test that quarantine metrics are recorded correctly."""
        # Setup error classifier to return DQ error
        mock_error_classifier.classify.return_value = ErrorType.DATA_QUALITY

        # Override transform to fail
        record_processor._transform.side_effect = Exception("DQ Fail")

        records = [{"id": 1}]
        batch_id = BatchID(uuid4())

        await record_processor.process_batch(records, batch_id)

        pipeline_label = "test_entity"
        run_type_label = mock_context.run_type.value

        # Expect quarantined count
        mock_metrics.increment_counter.assert_any_call(
            "records_processed_total",
            1,
            {
                "pipeline": pipeline_label,
                "stage": "quarantined",
                "run_type": run_type_label,
            },
        )

        # Expect error counter
        mock_metrics.increment_counter.assert_any_call(
            "errors_total",
            1,
            {
                "pipeline": pipeline_label,
                "stage": "transform",
                "error_code": ErrorType.DATA_QUALITY.value,
            },
        )
