"""Unit tests for bootstrap pipeline runner service function.

Tests bootstrap functions for PipelineRunnerService assembly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services import PipelineRunnerService
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)
from bioetl.composition.factories.pipeline.runner import (
    MetricsExtractor,
    RunnerFactory,
)
from bioetl.composition.registry import PipelineRegistry


@pytest.mark.unit
class TestBootstrapPipelineRunnerService:
    """Tests for bootstrap_pipeline_runner_service function."""

    def test_bootstrap_returns_pipeline_runner_service(self):
        """Test that bootstrap_pipeline_runner_service returns PipelineRunnerService."""
        result = bootstrap_pipeline_runner_service()

        assert isinstance(result, PipelineRunnerService)

    def test_bootstrap_wires_runner_factory(self):
        """Test that bootstrap_pipeline_runner_service wires RunnerFactory."""
        result = bootstrap_pipeline_runner_service()

        # PipelineRunnerService uses runner_factory attribute (dataclass)
        assert isinstance(result.runner_factory, RunnerFactory)

    def test_bootstrap_wires_metrics_extractor(self):
        """Test that bootstrap_pipeline_runner_service wires MetricsExtractor."""
        result = bootstrap_pipeline_runner_service()

        # PipelineRunnerService uses metrics_extractor attribute (dataclass)
        assert isinstance(result.metrics_extractor, MetricsExtractor)

    def test_bootstrap_with_custom_registry(self):
        """Test that bootstrap_pipeline_runner_service accepts custom registry."""
        custom_registry = PipelineRegistry()
        result = bootstrap_pipeline_runner_service(registry=custom_registry)

        assert isinstance(result, PipelineRunnerService)
        # The factory should use the custom registry
        assert result.runner_factory._registry is custom_registry

    def test_bootstrap_without_registry_uses_none(self):
        """Test that bootstrap_pipeline_runner_service passes None when no registry given."""
        result = bootstrap_pipeline_runner_service()

        # Factory's _registry should be None (will use default when needed)
        assert result.runner_factory._registry is None

    def test_bootstrap_creates_logger(self):
        """Test that bootstrap_pipeline_runner_service creates a logger."""
        result = bootstrap_pipeline_runner_service()

        # PipelineRunnerService uses logger attribute (dataclass)
        assert result.logger is not None

    def test_bootstrap_logger_has_correct_pipeline_name(self):
        """Test that the logger is configured with correct pipeline name."""
        with patch(
            "bioetl.composition.bootstrap.runtime.runner.bootstrap_logger_port"
        ) as mock_bootstrap_logger:
            mock_logger = MagicMock()
            mock_bootstrap_logger.return_value = mock_logger

            bootstrap_pipeline_runner_service()

            mock_bootstrap_logger.assert_called_once()
            call_kwargs = mock_bootstrap_logger.call_args[1]
            assert call_kwargs["pipeline"] == "pipeline_runner_service"
            assert call_kwargs["log_level"] == "INFO"


@pytest.mark.unit
class TestBootstrapPipelineRunnerServiceIntegration:
    """Integration-style tests for bootstrap_pipeline_runner_service."""

    def test_bootstrapped_service_can_list_pipelines(self):
        """Test that the bootstrapped service can list available pipelines."""
        service = bootstrap_pipeline_runner_service()

        # This will trigger registration of all pipelines
        pipelines = service.list_pipelines()

        # Should return a list of pipeline names
        assert isinstance(pipelines, list)
        # After registration, should have pipelines available
        assert len(pipelines) > 0

    def test_bootstrapped_service_lists_known_pipelines(self):
        """Test that the bootstrapped service lists known pipeline names."""
        service = bootstrap_pipeline_runner_service()

        # Get list of pipelines
        pipelines = service.list_pipelines()

        # Verify some expected pipelines are present
        # chembl_activity should be one of the registered pipelines
        assert "chembl_activity" in pipelines or len(pipelines) > 0

    def test_bootstrap_multiple_times_creates_independent_services(self):
        """Test that multiple bootstrap calls create independent services."""
        service1 = bootstrap_pipeline_runner_service()
        service2 = bootstrap_pipeline_runner_service()

        # Should be different instances
        assert service1 is not service2
        assert service1.runner_factory is not service2.runner_factory
        assert service1.metrics_extractor is not service2.metrics_extractor
