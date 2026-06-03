"""Contract tests for composition _pipeline_execution."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.composition import _pipeline_execution

pytestmark = pytest.mark.unit


class TestDataclasses:
    """Test dataclass definitions."""

    def test_pipeline_execution_dataclasses__vacuum_options_default_values(self) -> None:
        """VacuumOptions should have default values."""
        options = _pipeline_execution.VacuumOptions()
        assert options.retention_days == 7
        assert options.dry_run is False

    def test_vacuum_options_custom_values(self) -> None:
        """VacuumOptions should accept custom values."""
        options = _pipeline_execution.VacuumOptions(retention_days=30, dry_run=True)
        assert options.retention_days == 30
        assert options.dry_run is True

    def test_vacuum_options_frozen(self) -> None:
        """VacuumOptions should be frozen (immutable)."""
        options = _pipeline_execution.VacuumOptions()
        with pytest.raises(FrozenInstanceError):
            options.retention_days = 10

    def test_archive_options_required_field(self) -> None:
        """ArchiveOptions should require target_path."""
        options = _pipeline_execution.ArchiveOptions(target_path="/tmp/archive")
        assert options.target_path == "/tmp/archive"
        assert options.remove_source is False

    def test_archive_options_custom_values(self) -> None:
        """ArchiveOptions should accept custom values."""
        options = _pipeline_execution.ArchiveOptions(
            target_path="/tmp/archive", remove_source=True
        )
        assert options.target_path == "/tmp/archive"
        assert options.remove_source is True

    def test_archive_options_frozen(self) -> None:
        """ArchiveOptions should be frozen (immutable)."""
        options = _pipeline_execution.ArchiveOptions(target_path="/tmp/archive")
        with pytest.raises(FrozenInstanceError):
            options.target_path = "/tmp/other"


class TestGetSettings:
    """Test get_settings function."""

    @patch("bioetl.composition.runtime_builders.config_access.get_settings")
    def test_get_settings_calls_impl(self, mock_get_settings: MagicMock) -> None:
        """Should call get_settings from runtime_builders."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        result = _pipeline_execution.get_settings()

        mock_get_settings.assert_called_once()
        assert result == mock_settings


class TestMaybeStartMetricsServer:
    """Test maybe_start_metrics_server function."""

    @patch("bioetl.composition.bootstrap.runtime.observability.maybe_start_metrics_server")
    def test_maybe_start_metrics_server_calls_impl(self, mock_impl: MagicMock) -> None:
        """Should call implementation from bootstrap runtime."""
        mock_settings = MagicMock()
        mock_result = MagicMock()
        mock_impl.return_value = mock_result

        result = _pipeline_execution.maybe_start_metrics_server(mock_settings)

        mock_impl.assert_called_once_with(mock_settings)
        assert result == mock_result


class TestBuildPipelineContext:
    """Test build_pipeline_context function."""

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_context_builder.build_pipeline_context"
    )
    def test_build_pipeline_context_forwards_args(self, mock_impl: MagicMock) -> None:
        """Should forward all arguments to implementation."""
        mock_context = MagicMock()
        mock_impl.return_value = mock_context

        result = _pipeline_execution.build_pipeline_context("test_pipeline", {"key": "value"})

        mock_impl.assert_called_once_with("test_pipeline", {"key": "value"})
        assert result == mock_context


class TestPushMetricsToGateway:
    """Test push_metrics_to_gateway function."""

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_pipeline_execution_push_metrics__gateway_basic_call(self, mock_impl: MagicMock) -> None:
        """Should call implementation with basic parameters."""
        mock_impl.return_value = True

        result = _pipeline_execution.push_metrics_to_gateway()

        mock_impl.assert_called_once_with(
            run_label="bioetl", pipeline_name=None, run_type=None
        )
        assert result is True

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_pipeline_execution_push_metrics__gateway_with_all_parameters(self, mock_impl: MagicMock) -> None:
        """Should call implementation with all parameters."""
        mock_impl.return_value = True

        grouping_key_extra = {"key1": "value1"}
        metric_names = ("metric1", "metric2")

        result = _pipeline_execution.push_metrics_to_gateway(
            run_label="custom",
            pipeline_name="test_pipeline",
            run_type="manual",
            grouping_key_extra=grouping_key_extra,
            metric_names=metric_names,
        )

        mock_impl.assert_called_once_with(
            run_label="custom",
            pipeline_name="test_pipeline",
            run_type="manual",
            grouping_key_extra=grouping_key_extra,
            metric_names=metric_names,
        )
        assert result is True

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_pipeline_execution_push_metrics__gateway_with_grouping_key_only(self, mock_impl: MagicMock) -> None:
        """Should include grouping_key_extra when provided."""
        mock_impl.return_value = True

        grouping_key_extra = {"env": "test"}

        _pipeline_execution.push_metrics_to_gateway(grouping_key_extra=grouping_key_extra)

        call_kwargs = mock_impl.call_args[1]
        assert "grouping_key_extra" in call_kwargs

    @patch("bioetl.composition.observability_api.push_metrics_to_gateway")
    def test_pipeline_execution_push_metrics__gateway_with_metric_names_only(self, mock_impl: MagicMock) -> None:
        """Should include metric_names when provided."""
        mock_impl.return_value = True

        metric_names = ("metric1", "metric2")

        _pipeline_execution.push_metrics_to_gateway(metric_names=metric_names)

        call_kwargs = mock_impl.call_args[1]
        assert "metric_names" in call_kwargs


class TestEnsureMetricsServerStarted:
    """Test ensure_metrics_server_started function."""

    @patch("bioetl.composition.runtime_builders.config_access.get_settings")
    @patch("bioetl.composition.bootstrap.runtime.observability.maybe_start_metrics_server")
    def test_ensure_metrics_server_started_success(
        self, mock_maybe_start: MagicMock, mock_get_settings: MagicMock
    ) -> None:
        """Should return True when server starts successfully."""
        mock_settings = MagicMock()
        mock_settings.observability.metrics_enabled = True
        mock_get_settings.return_value = mock_settings
        mock_maybe_start.return_value = True

        result = _pipeline_execution.ensure_metrics_server_started()

        assert result is True
        mock_get_settings.assert_called_once()
        mock_maybe_start.assert_called_once_with(mock_settings)

    @patch("bioetl.composition.runtime_builders.config_access.get_settings")
    @patch("bioetl.composition.bootstrap.runtime.observability.maybe_start_metrics_server")
    def test_ensure_metrics_server_started_disabled(
        self, mock_maybe_start: MagicMock, mock_get_settings: MagicMock
    ) -> None:
        """Should return False when metrics disabled."""
        mock_settings = MagicMock()
        mock_settings.observability.metrics_enabled = False
        mock_get_settings.return_value = mock_settings
        mock_maybe_start.return_value = False

        result = _pipeline_execution.ensure_metrics_server_started()

        assert result is False


class _StubExecutionMetricsRunner:
    """Minimal protocol-compatible runner for execution contract tests."""

    def __init__(self) -> None:
        self._shutdown_signal: object | None = None

    async def run(self) -> None:
        """Satisfy RunnablePort without side effects."""

    @property
    def shutdown_signal(self) -> object | None:
        """Return an optional shutdown signal."""
        return self._shutdown_signal

    @property
    def run_id(self) -> str:
        """Return a stable run identifier."""
        return "test-run-id"

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Return canonical execution counters."""
        return {
            "records_fetched": 0,
            "records_bronze": 0,
            "records_silver": 0,
            "records_gold": 0,
            "records_gold_excluded_by_contract": 0,
            "records_quarantined": 0,
            "records_filtered_out": 0,
        }


class TestRequireExecutionMetricsRunner:
    """Test execution-metrics runner contract enforcement."""

    def test_require_execution_metrics_runner_accepts_protocol_implementation(
        self,
    ) -> None:
        """Protocol-compatible runners should pass through unchanged."""
        runner = _StubExecutionMetricsRunner()

        result = _pipeline_execution._require_execution_metrics_runner(runner)

        assert result is runner

    def test_require_execution_metrics_runner_raises_type_error(self) -> None:
        """Objects outside ExecutionMetricsRunnerPort should fail fast."""
        with pytest.raises(
            TypeError,
            match="Runner does not implement ExecutionMetricsRunnerPort",
        ):
            _pipeline_execution._require_execution_metrics_runner(object())


class TestAllExports:
    """Test __all__ exports."""

    def test_pipeline_execution_exports__all_declares_public_exports(self) -> None:
        """__all__ should declare all public exports."""
        expected_exports = [
            "ArchiveOptions",
            "VacuumOptions",
            "build_pipeline_context",
            "create_pipeline_runner",
            "ensure_metrics_server_started",
            "push_metrics_to_gateway",
            "run_pipeline",
        ]

        assert _pipeline_execution.__all__ == expected_exports


class TestCreatePipelineRunner:
    """Test create_pipeline_runner function."""

    @patch("bioetl.composition._pipeline_execution.build_pipeline_context")
    @patch("bioetl.composition._pipeline_execution._create_pipeline_runner_from_context")
    @patch("bioetl.infrastructure.time.SystemClock")
    def test_create_pipeline_runner_calls_build_context(
        self, mock_clock: MagicMock, mock_create_from_context: MagicMock, mock_build_context: MagicMock
    ) -> None:
        """Should call build_pipeline_context with correct arguments."""
        from bioetl.application.services.execution.pipeline_runner_models import RunOptions

        mock_context = MagicMock()
        mock_build_context.return_value = mock_context
        mock_runner = MagicMock()
        mock_create_from_context.return_value = mock_runner

        options = RunOptions(run_type="incremental")
        result = _pipeline_execution.create_pipeline_runner("test_pipeline", options)

        mock_build_context.assert_called_once()
        mock_create_from_context.assert_called_once_with(mock_context)
        assert result == mock_runner
