"""Unit tests for ServicesBuilder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.services.builder import ServicesBuilder
from bioetl.composition.factories.services.pipeline_builder import (
    BatchExecutorBuildRequest,
)


@pytest.mark.unit
class TestServicesBuilderCreateCheckpointManager:
    """Tests for ServicesBuilder.create_checkpoint_manager."""

    @patch("bioetl.composition.factories.services.builder.create_checkpoint_manager")
    def test_delegates_to_module_function(self, mock_create: MagicMock) -> None:
        """Static method delegates to create_checkpoint_manager function."""
        expected = MagicMock()
        mock_create.return_value = expected

        result = ServicesBuilder.create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="test",
            run_id="r1",
            resume=False,
        )

        assert result is expected
        mock_create.assert_called_once()

    @patch("bioetl.composition.factories.services.builder.create_checkpoint_manager")
    def test_passes_loading_strategy(self, mock_create: MagicMock) -> None:
        """loading_strategy kwarg is forwarded."""
        mock_create.return_value = MagicMock()
        strategy = MagicMock()

        ServicesBuilder.create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="p",
            run_id="r",
            resume=True,
            loading_strategy=strategy,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["loading_strategy"] is strategy

    @patch("bioetl.composition.factories.services.builder.create_checkpoint_manager")
    def test_passes_metrics(self, mock_create: MagicMock) -> None:
        """metrics kwarg is forwarded."""
        mock_create.return_value = MagicMock()
        metrics = MagicMock()

        ServicesBuilder.create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="p",
            run_id="r",
            resume=True,
            metrics=metrics,
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["metrics"] is metrics

    @patch("bioetl.composition.factories.services.builder.create_checkpoint_manager")
    def test_passes_compatibility_kwargs(self, mock_create: MagicMock) -> None:
        """Compatibility kwargs are forwarded to module function."""
        mock_create.return_value = MagicMock()
        compatibility_service = MagicMock()
        current_metadata = MagicMock()

        ServicesBuilder.create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="p",
            run_id="r",
            resume=True,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=current_metadata,
            compatibility_policy="observe",
        )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["checkpoint_compatibility_service"] is compatibility_service
        assert call_kwargs["current_metadata"] is current_metadata
        assert call_kwargs["compatibility_policy"] == "observe"


@pytest.mark.unit
class TestServicesBuilderCreateBatchProcessingComponents:
    """Tests for ServicesBuilder.create_batch_processing_components."""

    @patch(
        "bioetl.composition.factories.services.builder.create_batch_processing_components"
    )
    def test_delegates_to_module_function(self, mock_create: MagicMock) -> None:
        """Static method delegates to create_batch_processing_components."""
        expected = MagicMock()
        mock_create.return_value = expected

        result = ServicesBuilder.create_batch_processing_components(
            services=MagicMock(),
            context=MagicMock(),
            config=MagicMock(),
            error_classifier=MagicMock(),
            transform_callback=MagicMock(),
            gold_filter_callback=MagicMock(),
            gold_transform_callback=MagicMock(),
            gold_validator=MagicMock(),
        )

        assert result is expected


@pytest.mark.unit
class TestServicesBuilderCreateRecordProcessorFromPipeline:
    """Tests for ServicesBuilder.create_record_processor_from_pipeline."""

    @patch("bioetl.composition.factories.services.builder.extract_pipeline_callbacks")
    @patch(
        "bioetl.composition.factories.services.builder.create_record_processor_from_pipeline"
    )
    def test_extracts_callbacks_and_delegates(
        self,
        mock_create_rp: MagicMock,
        mock_extract_cb: MagicMock,
    ) -> None:
        """Extracts callbacks then delegates to create_record_processor_from_pipeline."""
        callbacks = MagicMock()
        mock_extract_cb.return_value = callbacks
        expected = MagicMock()
        mock_create_rp.return_value = expected

        pipeline = MagicMock()
        pipeline.services.tracing = MagicMock()

        result = ServicesBuilder.create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=None,
            gold_schema=MagicMock(),
        )

        assert result is expected
        mock_extract_cb.assert_called_once_with(pipeline)


@pytest.mark.unit
class TestServicesBuilderCreateBatchExecutorFromPipeline:
    """Tests for ServicesBuilder.create_batch_executor_from_pipeline."""

    @patch("bioetl.composition.factories.services.builder.extract_pipeline_callbacks")
    @patch(
        "bioetl.composition.factories.services.builder.create_batch_executor_from_pipeline"
    )
    def test_extracts_callbacks_and_delegates(
        self,
        mock_create_be: MagicMock,
        mock_extract_cb: MagicMock,
    ) -> None:
        """Extracts callbacks then delegates to create_batch_executor_from_pipeline."""
        callbacks = MagicMock()
        mock_extract_cb.return_value = callbacks
        expected = MagicMock()
        mock_create_be.return_value = expected

        result = ServicesBuilder.create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=MagicMock(),
                callbacks=MagicMock(),
                silver_schema=None,
                gold_schema=MagicMock(),
                checkpoint_manager=MagicMock(),
                shutdown_signal=MagicMock(),
                create_batch_processing_components_fn=MagicMock(),
            )
        )

        assert result is expected
        mock_extract_cb.assert_called_once()
