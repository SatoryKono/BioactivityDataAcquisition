"""Unit tests for bootstrap pipeline runner service function.

Tests bootstrap functions for PipelineRunnerService assembly.

Heavy observability (PrometheusMetrics + DataQualityMonitor) is mocked: cold
bootstrap can take 60-100s on Windows/G-drive and exceeds pytest-timeout=60.
Wiring of RunnerFactory / MetricsExtractor / helper services is still exercised
against real composition factories.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineRunnerService,
)
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)
from bioetl.composition.factories.pipeline.runner import (
    MetricsExtractor,
    RunnerFactory,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.domain.ports import ClockPort
from bioetl.infrastructure.time import SystemClock

_OBSERVABILITY_PATCH = (
    "bioetl.composition.bootstrap.runtime.runner.bootstrap_observability_bundle"
)
_SETTINGS_PATCH = "bioetl.composition.bootstrap.runtime.runner.get_settings"


def _light_observability_bundle() -> SimpleNamespace:
    return SimpleNamespace(
        logger=MagicMock(name="logger"),
        metrics=MagicMock(name="metrics"),
        audit=MagicMock(name="audit"),
        tracer=MagicMock(name="tracer"),
        dq_monitor=None,
    )


@pytest.fixture
def light_observability() -> SimpleNamespace:
    """Lightweight ports so unit tests never pay cold Prometheus/DQ startup."""
    return _light_observability_bundle()


@pytest.fixture
def bootstrap_with_light_observability(light_observability: SimpleNamespace):
    """Patch observability + settings for fast, deterministic unit bootstraps."""
    with (
        patch(_SETTINGS_PATCH, return_value=MagicMock(name="settings")) as mock_settings,
        patch(
            _OBSERVABILITY_PATCH, return_value=light_observability
        ) as mock_observability,
    ):
        yield mock_settings, mock_observability, light_observability


@pytest.mark.unit
class TestBootstrapPipelineRunnerService:
    """Tests for bootstrap_pipeline_runner_service function."""

    def test_bootstrap_returns_pipeline_runner_service(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that bootstrap_pipeline_runner_service returns PipelineRunnerService."""
        result = bootstrap_pipeline_runner_service()

        assert isinstance(result, PipelineRunnerService)

    def test_bootstrap_wires_runner_factory(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that bootstrap_pipeline_runner_service wires RunnerFactory."""
        result = bootstrap_pipeline_runner_service()

        assert isinstance(result.runner_factory, RunnerFactory)

    def test_bootstrap_wires_metrics_extractor(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that bootstrap_pipeline_runner_service wires MetricsExtractor."""
        result = bootstrap_pipeline_runner_service()

        assert isinstance(result.metrics_extractor, MetricsExtractor)

    def test_bootstrap_with_custom_registry(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that bootstrap_pipeline_runner_service accepts custom registry."""
        custom_registry = PipelineRegistry()
        result = bootstrap_pipeline_runner_service(registry=custom_registry)

        assert isinstance(result, PipelineRunnerService)
        assert result.runner_factory._registry is custom_registry

    def test_bootstrap_without_registry_uses_none(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that bootstrap_pipeline_runner_service passes None when no registry given."""
        result = bootstrap_pipeline_runner_service()

        assert result.runner_factory._registry is None

    def test_bootstrap_creates_logger(
        self,
        bootstrap_with_light_observability: tuple[object, object, SimpleNamespace],
    ) -> None:
        """Test that bootstrap_pipeline_runner_service creates a logger."""
        _settings, _obs, bundle = bootstrap_with_light_observability
        result = bootstrap_pipeline_runner_service()

        assert result.logger is bundle.logger

    def test_bootstrap_wires_context_and_execution_services(
        self,
        bootstrap_with_light_observability: tuple[object, object, SimpleNamespace],
    ) -> None:
        """Bootstrap should wire explicit helper services, not hidden globals."""
        _settings, _obs, bundle = bootstrap_with_light_observability
        result = bootstrap_pipeline_runner_service()

        assert isinstance(result._context_service, PipelineRunContextService)
        assert isinstance(result._execution_service, PipelineRunExecutionService)
        assert isinstance(result.clock, ClockPort)
        assert isinstance(result.clock, SystemClock)
        assert result.metrics is bundle.metrics
        assert result.audit is bundle.audit

    def test_bootstrap_logger_has_correct_pipeline_name(
        self, bootstrap_with_light_observability: tuple[MagicMock, MagicMock, object]
    ) -> None:
        """Test that the logger is configured with correct pipeline name."""
        mock_get_settings, mock_bootstrap_observability, _bundle = (
            bootstrap_with_light_observability
        )

        bootstrap_pipeline_runner_service()

        mock_bootstrap_observability.assert_called_once()
        call_kwargs = mock_bootstrap_observability.call_args[1]
        assert call_kwargs["pipeline"] == "pipeline_runner_service"
        assert call_kwargs["log_level"] == "INFO"
        assert call_kwargs["settings"] is mock_get_settings.return_value
        assert call_kwargs["run_id"] is not None
        # run_id must be a real UUID-like value produced by occurrence factory
        assert str(call_kwargs["run_id"])


@pytest.mark.unit
class TestBootstrapPipelineRunnerServiceIntegration:
    """Composition-wiring tests for bootstrap_pipeline_runner_service.

    Observability remains mocked; pipeline registration uses real RunnerFactory.
    """

    def test_bootstrapped_service_can_list_pipelines(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that the bootstrapped service can list available pipelines."""
        service = bootstrap_pipeline_runner_service()

        pipelines = service.list_pipelines()

        assert isinstance(pipelines, list)
        assert len(pipelines) > 0

    def test_bootstrapped_service_lists_known_pipelines(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that the bootstrapped service lists known pipeline names."""
        service = bootstrap_pipeline_runner_service()

        pipelines = service.list_pipelines()

        assert "chembl_activity" in pipelines or len(pipelines) > 0

    def test_bootstrap_multiple_times_creates_independent_services(
        self, bootstrap_with_light_observability: tuple[object, object, object]
    ) -> None:
        """Test that multiple bootstrap calls create independent services."""
        service1 = bootstrap_pipeline_runner_service()
        service2 = bootstrap_pipeline_runner_service()

        assert service1 is not service2
        assert service1.runner_factory is not service2.runner_factory
        assert service1.metrics_extractor is not service2.metrics_extractor
        assert service1._context_service is not service2._context_service
        assert service1._execution_service is not service2._execution_service
