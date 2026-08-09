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
"""Unit tests for RecordProcessor metrics recording."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

import pytest

from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier, ErrorType
from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import RunType, ValidationResult
from tests.testing_support.application_batch_components import (
    build_test_batch_processing_components,
)


@pytest.fixture
def mock_metrics():
    """Create mock metrics."""
    return MagicMock(spec=MetricsPort)


@pytest.fixture
def mock_services(mock_metrics):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineService)
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
        run_id=deterministic_uuid_from_callsite("test_record_processor_metrics"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_gold_validator():
    """Create mock gold validator."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


def _create_record_processor(
    *,
    services,
    context,
    config,
    error_classifier,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    gold_validator,
    span_executor_factory=None,
) -> RecordProcessor:
    """Build RecordProcessor with composition-level dependency wiring."""
    tracer = NoOpTracing()
    components = build_test_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator,
        tracer=tracer,
    )
    if span_executor_factory is not None:
        return RecordProcessor(
            context=context,
            batch_metrics=components.batch_metrics,
            transformer=components.transformer,
            writer=components.writer,
            config=config,
            tracer=tracer,
            span_executor_factory=span_executor_factory,
        )
    return RecordProcessor(
        context=context,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        config=config,
        tracer=tracer,
    )


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
        gold_schema=MagicMock(),
    )
    return _create_record_processor(
        services=mock_services,
        context=mock_context,
        config=config,
        error_classifier=mock_error_classifier,
        transform_callback=AsyncMock(return_value={"id": 1}),
        gold_filter_callback=MagicMock(return_value=True),
        gold_transform_callback=MagicMock(side_effect=lambda c, r: r),
        gold_validator=mock_gold_validator,
    )


@pytest.mark.unit
class TestRecordProcessorMetrics:
    """Tests for RecordProcessor metrics logic."""

    def test_record_processor_uses_injected_span_executor_factory(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_validator,
    ) -> None:
        """RecordProcessor receives span executor creation through DI."""
        config = RecordProcessorConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )
        span_executor = MagicMock()
        span_executor_factory = MagicMock(return_value=span_executor)

        processor = _create_record_processor(
            services=mock_services,
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            transform_callback=AsyncMock(return_value={"id": 1}),
            gold_filter_callback=MagicMock(return_value=True),
            gold_transform_callback=MagicMock(side_effect=lambda c, r: r),
            gold_validator=mock_gold_validator,
            span_executor_factory=span_executor_factory,
        )

        span_executor_factory.assert_called_once()
        assert processor._span_executor is span_executor

    async def test_process_batch_records_batch_size_and_counts(
        self, record_processor, mock_metrics, mock_context
    ):
        """Test that batch size histogram and counters are recorded with correct labels."""
        records = [{"id": 1}, {"id": 2}]
        batch_id = deterministic_batch_uuid_from_callsite(
            "test_record_processor_metrics"
        )

        await record_processor.process_batch(records, batch_id)

        pipeline_label = "test_entity"
        run_type_label = mock_context.run_type.value

        mock_metrics.observe_histogram.assert_called_with(
            "bioetl_batch_size_records",
            2,
            {"pipeline": pipeline_label, "stage": "bronze"},
        )

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "bronze", "run_type": run_type_label},
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            2,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "fetched",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            2,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "bronze",
            },
        )

        # Silver count
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "silver", "run_type": run_type_label},
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            2,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "silver",
            },
        )

        # Gold count
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            2,
            {"pipeline": pipeline_label, "stage": "gold", "run_type": run_type_label},
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            2,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "gold",
            },
        )

    async def test_process_batch_records_quarantine_metrics(
        self,
        mock_services,
        mock_metrics,
        mock_context,
        mock_error_classifier,
        mock_gold_validator,
    ):
        """Test that quarantine metrics are recorded correctly."""
        from bioetl.domain.exceptions import DataQualityError

        # Setup error classifier to return DQ error
        mock_error_classifier.classify.return_value = ErrorType.DATA_QUALITY

        # Create processor with failing transform callback
        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise DataQualityError("DQ Fail")

        config = RecordProcessorConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )
        processor = _create_record_processor(
            services=mock_services,
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            transform_callback=failing_transform,
            gold_filter_callback=MagicMock(return_value=True),
            gold_transform_callback=MagicMock(side_effect=lambda c, r: r),
            gold_validator=mock_gold_validator,
        )

        records = [{"id": 1}]
        batch_id = deterministic_batch_uuid_from_callsite(
            "test_record_processor_metrics"
        )

        await processor.process_batch(records, batch_id)

        pipeline_label = "test_entity"
        run_type_label = mock_context.run_type.value

        # Expect quarantined count
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            1,
            {
                "pipeline": pipeline_label,
                "stage": "quarantined",
                "run_type": run_type_label,
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            1,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "fetched",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            1,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "bronze",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            1,
            {
                "pipeline": pipeline_label,
                "run_type": run_type_label,
                "flow_stage": "quarantined",
            },
        )

        # Expect error counter
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_errors_total",
            1,
            {
                "pipeline": pipeline_label,
                "stage": "transform",
                "error_code": ErrorType.DATA_QUALITY.value,
            },
        )
