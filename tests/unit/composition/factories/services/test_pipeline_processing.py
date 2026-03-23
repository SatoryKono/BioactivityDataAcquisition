"""Unit tests for pipeline_processing assembly helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)


@pytest.mark.unit
class TestBuildComponentsAndProcessingService:
    """Contract-level tests for pipeline_processing helpers."""

    @patch(
        "bioetl.composition.factories.services.pipeline_processing.BatchProcessingService"
    )
    def test_delegates_component_build_and_wraps_processing_service(
        self, mock_processing_service_cls: MagicMock
    ) -> None:
        """Assembly should preserve pipeline/callback wiring across both builders."""
        pipeline = SimpleNamespace(
            services=MagicMock(name="services"),
            context=MagicMock(name="context"),
        )
        callbacks = SimpleNamespace(
            transform=MagicMock(name="transform"),
            gold_transform=MagicMock(name="gold_transform"),
        )
        components = MagicMock(name="components")
        processing_service = MagicMock(name="processing_service")
        mock_processing_service_cls.return_value = processing_service
        create_components = MagicMock(return_value=components)
        processor_config = MagicMock(name="processor_config")
        error_classifier = MagicMock(name="error_classifier")
        gold_filter = MagicMock(name="gold_filter")
        gold_validator = MagicMock(name="gold_validator")
        tracer = MagicMock(name="tracer")
        lock_validator = MagicMock(name="lock_validator")
        tracing_manager = MagicMock(name="tracing_manager")
        batch_id_factory = MagicMock(name="batch_id_factory")

        result = build_components_and_processing_service(
            pipeline=pipeline,
            processor_config=processor_config,
            error_classifier=error_classifier,
            callbacks=callbacks,
            gold_filter=gold_filter,
            gold_validator=gold_validator,
            tracer=tracer,
            lock_validator=lock_validator,
            tracing_manager=tracing_manager,
            batch_id_factory=batch_id_factory,
            create_batch_processing_components_fn=create_components,
        )

        assert result == (components, processing_service)
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
            lock_validator=lock_validator,
        )
        mock_processing_service_cls.assert_called_once_with(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            components=components,
            tracing_manager=tracing_manager,
            batch_id_factory=batch_id_factory,
        )
