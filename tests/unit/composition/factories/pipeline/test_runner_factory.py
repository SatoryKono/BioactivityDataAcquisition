"""Unit tests for composition/factories/runner_factory.py.

Tests RunnerFactory and MetricsExtractor implementations
for the PipelineRunnerService.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.factories.pipeline.runner import (
    MetricsExtractor,
    RunnerFactory,
    create_metrics_extractor,
    create_runner_factory,
)


def _make_mock_runner() -> MagicMock:
    """Create a runner double satisfying the execution+metrics contract."""
    runner = MagicMock()
    runner.run = AsyncMock()
    runner.shutdown_signal = None
    runner.run_id = "run-123"
    runner.execution_metrics = {
        "records_fetched": 100,
        "records_bronze": 95,
        "records_silver": 90,
        "records_gold": 85,
        "records_quarantined": 10,
    }
    return runner


@pytest.mark.unit
class TestRunnerFactory:
    """Tests for RunnerFactory class."""

    def test_init_without_custom_registry_defers_creation(self):
        """Factory should defer runtime-registry creation until it is needed."""
        factory = RunnerFactory()
        assert factory._registry is None
        assert factory._registrations_done is False
        assert callable(factory._registry_factory)

    def test_init_with_custom_registry(self):
        """Test RunnerFactory initializes with custom registry."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)

        assert factory._registry is custom_registry
        assert factory._registrations_done is False

    def test_effective_registry_with_custom(self):
        """Test _effective_registry returns custom registry when provided."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)

        assert factory._effective_registry is custom_registry

    def test_effective_registry_without_custom(self):
        """Test _effective_registry creates and caches a runtime registry."""
        created_registry = PipelineRegistry()
        factory = RunnerFactory(registry_factory=lambda: created_registry)

        result = factory._effective_registry

        assert result is created_registry
        assert factory._registry is created_registry

    def test_ensure_registrations_called_once(self):
        """Test _ensure_registrations is idempotent."""
        empty_registry = PipelineRegistry()
        mock_providers = MagicMock()
        factory = RunnerFactory(
            registry=empty_registry,
            ensure_providers_loaded_fn=mock_providers,
        )

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ) as mock_pipelines,
        ):
            factory._ensure_registrations()
            assert factory._registrations_done is True
            mock_providers.assert_called_once()
            mock_pipelines.assert_called_once()

            factory._ensure_registrations()
            assert mock_providers.call_count == 1
            assert mock_pipelines.call_count == 1

    def test_ensure_registrations_passes_registry(self):
        """Test _ensure_registrations passes custom registry to register_all_pipelines."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ) as mock_pipelines,
        ):
            factory._ensure_registrations()

            mock_pipelines.assert_called_once_with(registry=custom_registry)

    def test_ensure_registrations_passes_created_registry(self):
        """Test lazily created registry is passed explicitly for registration."""
        created_registry = PipelineRegistry()
        factory = RunnerFactory(registry_factory=lambda: created_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ) as mock_pipelines,
        ):
            factory._ensure_registrations()

        mock_pipelines.assert_called_once_with(registry=created_registry)

    def test_ensure_registrations_skips_pipeline_registration_when_populated(self):
        """Existing populated registries should not be re-registered."""
        populated_registry = MagicMock()
        populated_registry.list_pipelines.return_value = ["chembl_activity"]
        mock_providers = MagicMock()
        factory = RunnerFactory(
            registry=populated_registry,
            ensure_providers_loaded_fn=mock_providers,
        )

        with patch(
            "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
        ) as mock_pipelines:
            factory._ensure_registrations()

        mock_providers.assert_called_once()
        mock_pipelines.assert_not_called()

    def test_effective_registry_reuses_lazy_registry_instance(self):
        """Lazy runtime registry should be created once and then reused."""
        created_registry = PipelineRegistry()
        registry_factory = MagicMock(return_value=created_registry)
        factory = RunnerFactory(registry_factory=registry_factory)

        first = factory._effective_registry
        second = factory._effective_registry

        assert first is created_registry
        assert second is created_registry
        registry_factory.assert_called_once()


@pytest.mark.unit
class TestRunnerFactoryCreate:
    """Tests for RunnerFactory.create method."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock PipelineRunContext."""
        from uuid import uuid4

        from bioetl.domain.types import RunID, RunType

        context = MagicMock()
        context.pipeline_name = "chembl_activity"
        context.run_id = RunID(uuid4())
        context.run_type = RunType.INCREMENTAL
        return context

    def test_create_returns_runner(self, mock_context):
        """Test create returns a runner instance."""
        factory = RunnerFactory()
        mock_runner = _make_mock_runner()

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.build_pipeline_runner",
                return_value=mock_runner,
            ),
        ):
            result = factory.create(mock_context)

            assert result is mock_runner

    def test_create_uses_registry(self, mock_context):
        """Test create uses the configured registry."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)
        mock_runner = _make_mock_runner()

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.build_pipeline_runner",
                return_value=mock_runner,
            ) as mock_bootstrap,
        ):
            factory.create(mock_context)

            mock_bootstrap.assert_called_once_with(
                mock_context, registry=custom_registry
            )

    def test_create_uses_created_registry(self, mock_context):
        """Test create threads the lazily created registry into runner builder."""
        created_registry = PipelineRegistry()
        mock_runner = _make_mock_runner()
        factory = RunnerFactory(registry_factory=lambda: created_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.build_pipeline_runner",
                return_value=mock_runner,
            ) as mock_bootstrap,
        ):
            factory.create(mock_context)

        mock_bootstrap.assert_called_once_with(mock_context, registry=created_registry)

    def test_create_reuses_same_lazy_registry_across_multiple_calls(self, mock_context):
        """Repeated create calls should reuse one lazy runtime registry instance."""
        created_registry = PipelineRegistry()
        registry_factory = MagicMock(return_value=created_registry)
        mock_runner = _make_mock_runner()
        factory = RunnerFactory(registry_factory=registry_factory)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.build_pipeline_runner",
                return_value=mock_runner,
            ) as mock_bootstrap,
        ):
            factory.create(mock_context)
            factory.create(mock_context)

        registry_factory.assert_called_once()
        assert mock_bootstrap.call_count == 2
        for call in mock_bootstrap.call_args_list:
            assert call.kwargs["registry"] is created_registry

    def test_create_rejects_runner_without_metrics_contract(self, mock_context):
        """Test create fails fast for runners missing execution metrics."""
        factory = RunnerFactory()

        class MinimalRunner:
            shutdown_signal = None
            run_id = "run-123"

            async def run(self) -> None:
                await asyncio.sleep(0)
                return None

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.build_pipeline_runner",
                return_value=MinimalRunner(),
            ),
        ):
            with pytest.raises(TypeError, match="ExecutionMetricsRunnerPort"):
                factory.create(mock_context)


@pytest.mark.unit
class TestRunnerFactoryListPipelines:
    """Tests for RunnerFactory.list_pipelines method."""

    def test_list_pipelines_returns_list(self):
        """Test list_pipelines returns a list of pipeline names."""
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = ["pipeline1", "pipeline2"]

        factory = RunnerFactory(registry=mock_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
        ):
            result = factory.list_pipelines()

            assert result == ["pipeline1", "pipeline2"]
            assert mock_registry.list_pipelines.call_count == 2

    def test_list_pipelines_triggers_registrations(self):
        """Test list_pipelines triggers registrations."""
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = []
        mock_providers = MagicMock()
        factory = RunnerFactory(
            registry=mock_registry,
            ensure_providers_loaded_fn=mock_providers,
        )

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ) as mock_pipelines,
        ):
            factory.list_pipelines()

            mock_providers.assert_called_once()
            mock_pipelines.assert_called_once()


@pytest.mark.unit
class TestRunnerFactoryContains:
    """Tests for RunnerFactory.contains method."""

    def test_contains_returns_true_for_existing_pipeline(self):
        """Test contains returns True for registered pipeline."""
        mock_registry = MagicMock()
        mock_registry.contains.return_value = True

        factory = RunnerFactory(registry=mock_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
        ):
            result = factory.contains("existing_pipeline")

            assert result is True
            mock_registry.contains.assert_called_once_with("existing_pipeline")

    def test_contains_returns_false_for_unknown_pipeline(self):
        """Test contains returns False for unknown pipeline."""
        mock_registry = MagicMock()
        mock_registry.contains.return_value = False

        factory = RunnerFactory(registry=mock_registry)

        with (
            patch(
                "bioetl.composition.factories.pipeline.runner.ensure_providers_loaded"
            ),
            patch(
                "bioetl.composition.factories.pipeline.runner.register_all_pipelines"
            ),
        ):
            result = factory.contains("nonexistent_pipeline")

            assert result is False


@pytest.mark.unit
class TestMetricsExtractor:
    """Tests for MetricsExtractor class."""

    def test_extract_metrics_from_runner_with_execution_metrics(self):
        """Test extract_metrics returns metrics from runner's public contract."""
        extractor = MetricsExtractor()

        mock_runner = MagicMock()
        mock_runner.execution_metrics = {
            "records_fetched": 100,
            "records_bronze": 95,
            "records_silver": 90,
            "records_gold": 85,
            "records_gold_excluded_by_contract": 4,
            "records_quarantined": 10,
            "records_filtered_out": 7,
        }

        result = extractor.extract_metrics(mock_runner)

        assert result == {
            "records_fetched": 100,
            "records_bronze": 95,
            "records_silver": 90,
            "records_gold": 85,
            "records_gold_excluded_by_contract": 4,
            "records_quarantined": 10,
            "records_filtered_out": 7,
        }

    def test_extract_metrics_from_runner_without_execution_metrics(self):
        """Test extract_metrics rejects runners without public metrics."""
        extractor = MetricsExtractor()

        mock_runner = MagicMock(spec=[])

        with pytest.raises(TypeError, match="execution_metrics"):
            extractor.extract_metrics(mock_runner)

    def test_extract_metrics_with_partial_execution_metrics(self):
        """Test extract_metrics rejects partial execution metrics payloads."""
        extractor = MetricsExtractor()

        mock_runner = MagicMock()
        mock_runner.execution_metrics = {"records_fetched": 1}

        with pytest.raises(KeyError):
            extractor.extract_metrics(mock_runner)

    def test_extract_metrics_with_none_execution_metrics(self):
        """Test extract_metrics rejects None public metrics."""
        extractor = MetricsExtractor()

        mock_runner = MagicMock()
        mock_runner.execution_metrics = None

        with pytest.raises(TypeError, match="execution_metrics"):
            extractor.extract_metrics(mock_runner)


@pytest.mark.unit
class TestFactoryFunctions:
    """Tests for module-level factory functions."""

    def test_create_runner_factory_returns_factory(self):
        """Test create_runner_factory returns a RunnerFactory."""
        registry_factory = MagicMock(return_value=PipelineRegistry())
        result = create_runner_factory(registry_factory=registry_factory)

        assert isinstance(result, RunnerFactory)
        assert result._registry is None
        assert result._registry_factory is registry_factory

    def test_create_runner_factory_with_custom_registry(self):
        """Test create_runner_factory accepts custom registry."""
        custom_registry = PipelineRegistry()
        result = create_runner_factory(registry=custom_registry)

        assert isinstance(result, RunnerFactory)
        assert result._registry is custom_registry

    def test_create_runner_factory_threads_runtime_dependencies(self):
        """Factory helper should preserve injected runtime dependency seams."""
        registry_factory = MagicMock(return_value=PipelineRegistry())
        runner_builder = MagicMock()
        ensure_providers_loaded_fn = MagicMock()

        result = create_runner_factory(
            registry_factory=registry_factory,
            runner_builder=runner_builder,
            ensure_providers_loaded_fn=ensure_providers_loaded_fn,
        )

        assert result._registry_factory is registry_factory
        assert result._runner_builder is runner_builder
        assert result._ensure_providers_loaded_fn is ensure_providers_loaded_fn

    def test_create_metrics_extractor_returns_extractor(self):
        """Test create_metrics_extractor returns a MetricsExtractor."""
        result = create_metrics_extractor()

        assert isinstance(result, MetricsExtractor)
