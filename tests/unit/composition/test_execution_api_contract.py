"""Contract tests for composition execution_api."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.composition import execution_api

pytestmark = pytest.mark.unit


class TestExecutionApiExports:
    """Test public exports and lazy export behavior."""

    def test_execution_api_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "ArchiveOptions",
            "PipelineRunResult",
            "RunOptions",
            "RunResult",
            "VacuumOptions",
            "build_pipeline_context",
            "create_pipeline_runner",
            "ensure_metrics_server_started",
            "get_pipeline_runner_service",
            "maybe_start_metrics_server",
            "push_metrics_to_gateway",
            "run_pipeline",
        ]

        assert execution_api.__all__ == expected_exports

    def test_execution_api_exports__public_exports_maps_to_modules(self) -> None:
        """_PUBLIC_EXPORTS should map exports to correct modules."""
        expected_mapping = {
            "ArchiveOptions": "bioetl.composition._pipeline_execution",
            "PipelineRunResult": "bioetl.application.services.execution.pipeline_runner_models",
            "RunOptions": "bioetl.application.services.execution.pipeline_runner_models",
            "RunResult": "bioetl.application.services.execution.pipeline_runner_models",
            "VacuumOptions": "bioetl.composition._pipeline_execution",
            "build_pipeline_context": "bioetl.composition._pipeline_execution",
            "create_pipeline_runner": "bioetl.composition._pipeline_execution",
            "ensure_metrics_server_started": "bioetl.composition._pipeline_execution",
            "get_pipeline_runner_service": "bioetl.composition._services",
            "maybe_start_metrics_server": "bioetl.composition.bootstrap.runtime.observability",
            "run_pipeline": "bioetl.composition._pipeline_execution",
        }

        assert execution_api._PUBLIC_EXPORTS == expected_mapping


class TestPushMetricsToGateway:
    """Test push_metrics_to_gateway function."""

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_execution_api_push_metrics__gateway_basic_call(self, mock_impl: MagicMock) -> None:
        """Should call implementation with basic parameters."""
        mock_impl.return_value = True

        result = execution_api.push_metrics_to_gateway()

        mock_impl.assert_called_once_with(run_label="bioetl", pipeline_name=None, run_type=None)
        assert result is True

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_execution_api_push_metrics__gateway_with_all_parameters(
        self, mock_impl: MagicMock
    ) -> None:
        """Should call implementation with all parameters."""
        mock_impl.return_value = True

        grouping_key_extra = {"key1": "value1", "key2": "value2"}
        metric_names = ("metric1", "metric2", "metric3")

        result = execution_api.push_metrics_to_gateway(
            run_label="custom_label",
            pipeline_name="test_pipeline",
            run_type="manual",
            grouping_key_extra=grouping_key_extra,
            metric_names=metric_names,
        )

        mock_impl.assert_called_once_with(
            run_label="custom_label",
            pipeline_name="test_pipeline",
            run_type="manual",
            grouping_key_extra=grouping_key_extra,
            metric_names=metric_names,
        )
        assert result is True

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_push_metrics_to_gateway_returns_bool(self, mock_impl: MagicMock) -> None:
        """Should convert implementation result to bool."""
        mock_impl.return_value = 1
        assert execution_api.push_metrics_to_gateway() is True

        mock_impl.return_value = 0
        assert execution_api.push_metrics_to_gateway() is False

        mock_impl.return_value = None
        assert execution_api.push_metrics_to_gateway() is False

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_execution_api_push_metrics__gateway_with_grouping_key_only(
        self, mock_impl: MagicMock
    ) -> None:
        """Should include grouping_key_extra when provided."""
        mock_impl.return_value = True

        grouping_key_extra = {"env": "test", "region": "us-east"}

        execution_api.push_metrics_to_gateway(grouping_key_extra=grouping_key_extra)

        call_kwargs = mock_impl.call_args[1]
        assert "grouping_key_extra" in call_kwargs
        assert call_kwargs["grouping_key_extra"] == grouping_key_extra

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_execution_api_push_metrics__gateway_with_metric_names_only(
        self, mock_impl: MagicMock
    ) -> None:
        """Should include metric_names when provided."""
        mock_impl.return_value = True

        metric_names = ("metric1", "metric2")

        execution_api.push_metrics_to_gateway(metric_names=metric_names)

        call_kwargs = mock_impl.call_args[1]
        assert "metric_names" in call_kwargs
        assert call_kwargs["metric_names"] == metric_names


class TestLazyExportBehavior:
    """Test lazy export installation and behavior."""

    def test_execution_api_lazy_exports__installed_on_module_load(self) -> None:
        """Lazy exports should be installed on module load."""
        # Check that lazy export attributes exist
        assert hasattr(execution_api, "build_pipeline_context")
        assert hasattr(execution_api, "create_pipeline_runner")
        assert hasattr(execution_api, "run_pipeline")
        assert hasattr(execution_api, "ensure_metrics_server_started")
        assert hasattr(execution_api, "get_pipeline_runner_service")
        assert hasattr(execution_api, "maybe_start_metrics_server")


class TestTypeCheckingStubs:
    """Test TYPE_CHECKING type stubs."""

    def test_execution_api_type_checking__imports_reference_valid_modules(self) -> None:
        """TYPE_CHECKING imports should reference valid modules."""
        # These imports are only available during type checking
        # We verify the modules exist in the codebase
        import bioetl.application.services.execution.pipeline_runner_models
        import bioetl.composition._pipeline_execution
        import bioetl.composition.bootstrap.runtime.observability
        import bioetl.composition.registry_api

        # Verify modules are importable
        assert bioetl.application.services.execution.pipeline_runner_models is not None
        assert bioetl.composition._pipeline_execution is not None
        assert bioetl.composition.bootstrap.runtime.observability is not None
        assert bioetl.composition.registry_api is not None