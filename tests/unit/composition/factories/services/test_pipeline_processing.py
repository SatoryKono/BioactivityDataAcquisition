"""Unit tests for pipeline_processing assembly helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

import pytest

from bioetl.composition.factories.services.pipeline_processing import (
    build_components_and_processing_service,
)


class TestBuildComponentsAndProcessingService:
    @patch("bioetl.composition.factories.services.pipeline_processing.BatchProcessingService")
    @patch("bioetl.composition.factories.services.pipeline_processing.BatchProcessingSupportService")
    @patch("bioetl.composition.factories.services.pipeline_processing.QuarantineManagerService")
    @patch("bioetl.composition.factories.services.pipeline_processing.create_batch_processing_components")
    def test_delegates_component_build_and_wraps_processing_service(
        self,
        mock_create_components,
        mock_quarantine_manager_cls,
        mock_support_service_cls,
        mock_processing_service_cls,
    ):
        """Should coordinate component creation and service assembly."""
        # Arrange
        pipeline = SimpleNamespace(
            services=SimpleNamespace(
                metrics=MagicMock(),
                quarantine=MagicMock(),
            ),
            context=SimpleNamespace(
                logger=MagicMock(),
                run_type=MagicMock(value="incremental"),
            ),
        )
        processor_config = SimpleNamespace(
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity_type="test_entity",
        )
        components = MagicMock()
        mock_create_components.return_value = components
        quarantine_manager = MagicMock()
        mock_quarantine_manager_cls.return_value = quarantine_manager
        support_service = MagicMock()
        mock_support_service_cls.return_value = support_service
        batch_processing_service = MagicMock()
        mock_processing_service_cls.return_value = batch_processing_service

        tracing_manager = MagicMock()
        batch_id_factory = MagicMock()
        error_classifier = MagicMock()
        transform_callback = MagicMock()
        gold_filter_callback = MagicMock()
        gold_transform_callback = MagicMock()
        gold_validator = MagicMock()
        tracer = MagicMock()
        lock_validator = MagicMock()

        # Act
        res_components, res_service = build_components_and_processing_service(
            pipeline=pipeline,
            processor_config=processor_config,
            error_classifier=error_classifier,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
            tracing_manager=tracing_manager,
            batch_id_factory=batch_id_factory,
            tracer=tracer,
            lock_validator=lock_validator,
        )

        # Assert
        assert res_components == components
        assert res_service == batch_processing_service

        mock_create_components.assert_called_once_with(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
            tracer=tracer,
            lock_validator=lock_validator,
        )
        mock_quarantine_manager_cls.assert_called_once_with(
            quarantine_port=pipeline.services.quarantine,
            pipeline_name=processor_config.pipeline_name,
            metrics=pipeline.services.metrics,
        )
        mock_support_service_cls.assert_called_once_with(
            services=pipeline.services,
            logger=pipeline.context.logger,
            batch_metrics=components.batch_metrics,
            transformer=components.transformer,
            writer=components.writer,
            tracing=tracing_manager,
            quarantine_manager=quarantine_manager,
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
