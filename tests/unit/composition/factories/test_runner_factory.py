"""Unit tests for composition/factories/runner_factory.py.

Tests RunnerFactory and MetricsExtractor implementations
for the PipelineRunnerService.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.runner_factory import (
    MetricsExtractor,
    RunnerFactory,
    create_metrics_extractor,
    create_runner_factory,
)
from bioetl.composition.registry import PipelineRegistry


@pytest.mark.unit
class TestRunnerFactory:
    """Tests for RunnerFactory class."""

    def test_init_with_default_registry(self):
        """Test RunnerFactory initializes with None registry by default."""
        factory = RunnerFactory()

        assert factory._registry is None
        assert factory._registrations_done is False

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
        """Test _effective_registry returns default registry when not provided."""
        factory = RunnerFactory()

        with patch(
            "bioetl.composition.factories.runner_factory.get_default_registry"
        ) as mock_get_default:
            default_registry = PipelineRegistry()
            mock_get_default.return_value = default_registry

            result = factory._effective_registry

            mock_get_default.assert_called_once()
            assert result is default_registry

    def test_ensure_registrations_called_once(self):
        """Test _ensure_registrations is idempotent."""
        factory = RunnerFactory()

        with (
            patch(
                "bioetl.composition.factories.runner_factory.register_all_providers"
            ) as mock_providers,
            patch(
                "bioetl.composition.factories.runner_factory.register_all_pipelines"
            ) as mock_pipelines,
        ):
            # First call
            factory._ensure_registrations()
            assert factory._registrations_done is True
            mock_providers.assert_called_once()
            mock_pipelines.assert_called_once()

            # Second call should not re-register
            factory._ensure_registrations()
            assert mock_providers.call_count == 1
            assert mock_pipelines.call_count == 1

    def test_ensure_registrations_passes_registry(self):
        """Test _ensure_registrations passes custom registry to register_all_pipelines."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)

        with (
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch(
                "bioetl.composition.factories.runner_factory.register_all_pipelines"
            ) as mock_pipelines,
        ):
            factory._ensure_registrations()

            mock_pipelines.assert_called_once_with(registry=custom_registry)


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
        mock_runner = MagicMock()

        with (
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch("bioetl.composition.factories.runner_factory.register_all_pipelines"),
            patch(
                "bioetl.composition.bootstrap.bootstrap_pipeline",
                return_value=mock_runner,
            ),
        ):
            result = factory.create(mock_context)

            assert result is mock_runner

    def test_create_uses_registry(self, mock_context):
        """Test create uses the configured registry."""
        custom_registry = PipelineRegistry()
        factory = RunnerFactory(registry=custom_registry)
        mock_runner = MagicMock()

        with (
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch("bioetl.composition.factories.runner_factory.register_all_pipelines"),
            patch(
                "bioetl.composition.bootstrap.bootstrap_pipeline",
                return_value=mock_runner,
            ) as mock_bootstrap,
        ):
            factory.create(mock_context)

            # Verify bootstrap_pipeline was called with the custom registry
            mock_bootstrap.assert_called_once_with(
                mock_context, registry=custom_registry
            )


@pytest.mark.unit
class TestRunnerFactoryListPipelines:
    """Tests for RunnerFactory.list_pipelines method."""

    def test_list_pipelines_returns_list(self):
        """Test list_pipelines returns a list of pipeline names."""
        # Use a custom registry that we control
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = ["pipeline1", "pipeline2"]

        factory = RunnerFactory(registry=mock_registry)

        with (
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch("bioetl.composition.factories.runner_factory.register_all_pipelines"),
        ):
            result = factory.list_pipelines()

            assert result == ["pipeline1", "pipeline2"]
            mock_registry.list_pipelines.assert_called_once()

    def test_list_pipelines_triggers_registrations(self):
        """Test list_pipelines triggers registrations."""
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = []

        factory = RunnerFactory(registry=mock_registry)

        with (
            patch(
                "bioetl.composition.factories.runner_factory.register_all_providers"
            ) as mock_providers,
            patch(
                "bioetl.composition.factories.runner_factory.register_all_pipelines"
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
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch("bioetl.composition.factories.runner_factory.register_all_pipelines"),
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
            patch("bioetl.composition.factories.runner_factory.register_all_providers"),
            patch("bioetl.composition.factories.runner_factory.register_all_pipelines"),
        ):
            result = factory.contains("nonexistent_pipeline")

            assert result is False


@pytest.mark.unit
class TestMetricsExtractor:
    """Tests for MetricsExtractor class."""

    def test_extract_metrics_from_runner_with_executor(self):
        """Test extract_metrics returns metrics from runner's executor."""
        extractor = MetricsExtractor()

        # Create mock runner with executor
        mock_runner = MagicMock()
        mock_executor = MagicMock()
        mock_executor.records_fetched = 100
        mock_executor.records_bronze = 95
        mock_executor.records_silver = 90
        mock_executor.records_gold = 85
        mock_executor.records_quarantined = 10
        mock_runner._executor = mock_executor

        result = extractor.extract_metrics(mock_runner)

        assert result == {
            "records_fetched": 100,
            "records_bronze": 95,
            "records_silver": 90,
            "records_gold": 85,
            "records_quarantined": 10,
        }

    def test_extract_metrics_from_runner_without_executor(self):
        """Test extract_metrics returns zeros when runner has no executor."""
        extractor = MetricsExtractor()

        # Create mock runner without executor
        mock_runner = MagicMock(spec=[])  # No _executor attribute

        result = extractor.extract_metrics(mock_runner)

        assert result == {
            "records_fetched": 0,
            "records_bronze": 0,
            "records_silver": 0,
            "records_gold": 0,
            "records_quarantined": 0,
        }

    def test_extract_metrics_with_missing_executor_attributes(self):
        """Test extract_metrics handles missing executor attributes gracefully."""
        extractor = MetricsExtractor()

        # Create mock runner with partial executor
        mock_runner = MagicMock()
        mock_executor = MagicMock(spec=[])  # No metric attributes
        mock_runner._executor = mock_executor

        result = extractor.extract_metrics(mock_runner)

        # Should return 0 for all missing attributes
        assert result == {
            "records_fetched": 0,
            "records_bronze": 0,
            "records_silver": 0,
            "records_gold": 0,
            "records_quarantined": 0,
        }

    def test_extract_metrics_with_none_executor(self):
        """Test extract_metrics handles None executor."""
        extractor = MetricsExtractor()

        mock_runner = MagicMock()
        mock_runner._executor = None

        result = extractor.extract_metrics(mock_runner)

        assert result == {
            "records_fetched": 0,
            "records_bronze": 0,
            "records_silver": 0,
            "records_gold": 0,
            "records_quarantined": 0,
        }


@pytest.mark.unit
class TestFactoryFunctions:
    """Tests for module-level factory functions."""

    def test_create_runner_factory_returns_factory(self):
        """Test create_runner_factory returns a RunnerFactory."""
        result = create_runner_factory()

        assert isinstance(result, RunnerFactory)
        assert result._registry is None

    def test_create_runner_factory_with_custom_registry(self):
        """Test create_runner_factory accepts custom registry."""
        custom_registry = PipelineRegistry()
        result = create_runner_factory(registry=custom_registry)

        assert isinstance(result, RunnerFactory)
        assert result._registry is custom_registry

    def test_create_metrics_extractor_returns_extractor(self):
        """Test create_metrics_extractor returns a MetricsExtractor."""
        result = create_metrics_extractor()

        assert isinstance(result, MetricsExtractor)
