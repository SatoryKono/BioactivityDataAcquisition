"""Unit tests for pipeline_processing assembly helpers."""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

from bioetl.application.core.wiring.runtime import RecordProcessorConfig

from bioetl.application.core.wiring.runtime import BasePipeline
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)


pytestmark = pytest.mark.unit

def _make_callbacks() -> PipelineCallbacksContext:
    return cast(
        PipelineCallbacksContext,
        SimpleNamespace(
            transform=MagicMock(name="transform"),
            gold_transform=MagicMock(name="gold_transform"),
        ),
    )


class TestBuildComponentsAndProcessingService:
    @patch(
        "bioetl.composition.factories.services.pipeline_processing.BatchProcessingService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_processing.BatchProcessingSupportService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_processing.QuarantineRuntimeService"
    )
    def test_delegates_component_build_and_wraps_processing_service(
        self,
        mock_quarantine_manager_cls: MagicMock,
        mock_support_service_cls: MagicMock,
        mock_processing_service_cls: MagicMock,
    ) -> None:
        """Should coordinate component creation and service assembly."""
        # Arrange
        pipeline = SimpleNamespace(
            services=SimpleNamespace(
                metrics=MagicMock(),
                quarantine=MagicMock(),
            ),
            context=SimpleNamespace(
                logger=MagicMock(),
                run_id="run-123",
                run_type=MagicMock(value="incremental"),
            ),
        )
        processor_config = cast(
            RecordProcessorConfig,
            SimpleNamespace(
                pipeline_name="test_pipeline",
                provider="test_provider",
                entity_type="test_entity",
            ),
        )
        callbacks = _make_callbacks()
        components = MagicMock()
        create_components = MagicMock(return_value=components)
        quarantine_manager = MagicMock()
        mock_quarantine_manager_cls.return_value = quarantine_manager
        support_service = MagicMock()
        mock_support_service_cls.return_value = support_service
        batch_processing_service = MagicMock()
        mock_processing_service_cls.return_value = batch_processing_service

        tracing_manager = MagicMock()
        batch_id_factory = MagicMock()
        error_classifier = MagicMock()
        gold_filter = MagicMock()
        gold_validator = MagicMock()
        tracer = MagicMock()
        lock_validator = MagicMock()

        # Act
        res_components, res_service = build_components_and_processing_service(
            pipeline=cast(BasePipeline, pipeline),
            processor_config=processor_config,
            error_classifier=error_classifier,
            callbacks=callbacks,
            gold_filter=gold_filter,
            gold_validator=gold_validator,
            tracing_manager=tracing_manager,
            batch_id_factory=batch_id_factory,
            tracer=tracer,
            lock_validator=lock_validator,
            create_batch_processing_components_fn=create_components,
        )

        # Assert
        assert res_components == components
        assert res_service == batch_processing_service

        create_components.assert_called_once_with(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            transform_callback=callbacks.transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=callbacks.gold_transform,
            gold_validator=gold_validator,
            tracer=tracer,
            domain_event_emitter=None,
            lock_validator=lock_validator,
        )
        mock_quarantine_manager_cls.assert_called_once_with(
            quarantine_port=pipeline.services.quarantine,
            pipeline_name=processor_config.pipeline_name,
            metrics=pipeline.services.metrics,
            batch_metrics=components.batch_metrics,
            run_type=pipeline.context.run_type.value,
            domain_event_emitter=None,
        )
        mock_support_service_cls.assert_called_once_with(
            services=pipeline.services,
            logger=pipeline.context.logger,
            batch_metrics=components.batch_metrics,
            transformer=components.transformer,
            writer=components.writer,
            tracing=tracing_manager,
            quarantine_manager=quarantine_manager,
            run_id=pipeline.context.run_id,
            domain_event_emitter=None,
        )
        mock_processing_service_cls.assert_called_once_with(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            components=components,
            tracing_manager=tracing_manager,
            batch_id_factory=batch_id_factory,
            support_service=support_service,
        )
