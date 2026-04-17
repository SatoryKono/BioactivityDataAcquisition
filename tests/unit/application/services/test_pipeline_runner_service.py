"""Unit tests for PipelineRunnerService.

Tests the universal pipeline runner service.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.application.services.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.pipeline_runner_service import (
    PipelineNotFoundError,
    PipelineRunnerService,
    RunOptions,
    RunResult,
    PipelineRunResult,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def mock_runner():
    """Create a mock runner that implements execution+metrics runner contract."""
    runner = MagicMock()
    runner.run = AsyncMock()
    runner.shutdown_signal = None
    runner.run_id = str(uuid4())
    runner.manifest_id = "manifest-123"
    runner.execution_metrics = {
        "records_fetched": 100,
        "records_bronze": 95,
        "records_silver": 90,
        "records_gold": 85,
        "records_quarantined": 5,
        "records_filtered_out": 7,
    }
    return runner


@pytest.fixture
def mock_runner_factory(mock_runner):
    """Create a mock runner factory."""
    factory = MagicMock()
    factory.create = MagicMock(return_value=mock_runner)
    factory.list_pipelines = MagicMock(return_value=["test_pipeline", "other_pipeline"])
    factory.contains = MagicMock(return_value=True)
    return factory


@pytest.fixture
def mock_metrics_extractor():
    """Create a mock metrics extractor."""
    extractor = MagicMock()
    extractor.extract_metrics = MagicMock(
        return_value={
            "records_fetched": 100,
            "records_bronze": 95,
            "records_silver": 90,
            "records_gold": 85,
            "records_quarantined": 5,
            "records_filtered_out": 7,
        }
    )
    return extractor


@pytest.fixture
def service(mock_runner_factory, mock_metrics_extractor, mock_logger):
    """Create a PipelineRunnerService instance."""
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 3, 31, 9, 0, tzinfo=UTC)
    return PipelineRunnerService(
        runner_factory=mock_runner_factory,
        metrics_extractor=mock_metrics_extractor,
        logger=mock_logger,
        clock=clock,
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(),
    )


# =============================================================================
# Test RunOptions
# =============================================================================


@pytest.mark.unit
class TestRunOptions:
    """Test RunOptions dataclass."""

    def test_default_options(self):
        """Test default RunOptions values."""
        options = RunOptions()

        assert options.run_type == "incremental"
        assert options.resume is False
        assert options.limit is None
        assert options.dry_run is False
        assert options.input_csv is None
        assert options.filter_column is None
        assert options.filter_field is None
        assert options.vacuum_after_run is None
        assert options.vacuum_retention_days is None
        assert options.log_level == "INFO"

    def test_custom_options(self):
        """Test RunOptions with custom values."""
        options = RunOptions(
            run_type="backfill",
            resume=True,
            limit=100,
            dry_run=True,
            input_csv="ids.csv",
            filter_column="molecule_id",
            filter_field="chembl_id",
            vacuum_after_run=True,
            vacuum_retention_days=30,
            log_level="DEBUG",
        )

        assert options.run_type == "backfill"
        assert options.resume is True
        assert options.limit == 100
        assert options.dry_run is True
        assert options.input_csv == "ids.csv"
        assert options.filter_column == "molecule_id"
        assert options.filter_field == "chembl_id"
        assert options.vacuum_after_run is True
        assert options.vacuum_retention_days == 30
        assert options.log_level == "DEBUG"


# =============================================================================
# Test RunResult
# =============================================================================


@pytest.mark.unit
class TestRunResult:
    """Test RunResult dataclass."""

    def test_success_result(self):
        """Test successful run result."""
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="incremental",
            records_fetched=100,
            records_silver=95,
            records_quarantined=5,
        )

        assert result.status == PipelineRunResult.SUCCESS
        assert result.is_success is True
        assert result.success_rate == pytest.approx(0.95)
        assert result.error_message is None

    def test_failed_result(self):
        """Test failed run result."""
        result = RunResult(
            status=PipelineRunResult.FAILED,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="incremental",
            error_message="Connection refused",
            error_type="NetworkError",
        )

        assert result.status == PipelineRunResult.FAILED
        assert result.is_success is False
        assert result.error_message == "Connection refused"
        assert result.error_type == "NetworkError"

    def test_dry_run_result(self):
        """Test dry-run result."""
        result = RunResult(
            status=PipelineRunResult.DRY_RUN,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="rebuild",
        )

        assert result.status == PipelineRunResult.DRY_RUN
        assert result.is_success is True

    def test_shutdown_result(self):
        """Test shutdown result."""
        result = RunResult(
            status=PipelineRunResult.SHUTDOWN,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="incremental",
        )

        assert result.status == PipelineRunResult.SHUTDOWN
        assert result.is_success is False

    def test_duration_calculation(self):
        """Test duration_seconds property."""
        started = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 1, 10, 5, 30, tzinfo=UTC)

        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="incremental",
            started_at=started,
            completed_at=completed,
        )

        assert result.duration_seconds == pytest.approx(330.0)  # 5 minutes 30 seconds

    def test_success_rate_zero_fetched(self):
        """Test success_rate when no records fetched."""
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="test_pipeline",
            run_id="12345",
            run_type="incremental",
            records_fetched=0,
            records_quarantined=0,
        )

        assert result.success_rate == pytest.approx(1.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_service_uses_clock_for_dry_run_timestamps(
    service: PipelineRunnerService,
) -> None:
    started_at = datetime(2026, 3, 31, 9, 0, tzinfo=UTC)
    completed_at = datetime(2026, 3, 31, 9, 5, tzinfo=UTC)
    service.clock.now.side_effect = [started_at, completed_at]

    result = await service.run(
        "test_pipeline",
        options=RunOptions(dry_run=True),
    )

    assert result.started_at == started_at
    assert result.completed_at == completed_at
    assert result.status == PipelineRunResult.DRY_RUN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_service_derives_completion_from_started_anchor(
    service: PipelineRunnerService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started_at = datetime(2026, 4, 13, 9, 0, tzinfo=UTC)
    service.clock.now.return_value = started_at
    monkeypatch.setattr(
        "bioetl.application.services.execution.pipeline_runner_service.capture_runtime_timing_anchor",
        MagicMock(return_value=(started_at, 10.0)),
    )
    monkeypatch.setattr(
        "bioetl.application.services.execution.pipeline_run_execution_service.derive_completion_timestamp",
        MagicMock(return_value=(started_at + timedelta(seconds=4.5), 4.5)),
    )

    result = await service.run("test_pipeline")

    assert result.started_at == started_at
    assert result.completed_at == started_at + timedelta(seconds=4.5)
    assert result.duration_seconds == pytest.approx(4.5)


# =============================================================================
# Test PipelineNotFoundError
# =============================================================================


@pytest.mark.unit
class TestPipelineNotFoundError:
    """Test PipelineNotFoundError exception."""

    def test_error_message(self):
        """Test error message formatting."""
        error = PipelineNotFoundError(
            pipeline_name="nonexistent",
            available=["pipeline_a", "pipeline_b"],
        )

        assert error.pipeline_name == "nonexistent"
        assert error.available == ["pipeline_a", "pipeline_b"]
        assert "nonexistent" in str(error)
        assert "pipeline_a" in str(error)


# =============================================================================
# Test PipelineRunnerService.run()
# =============================================================================


@pytest.mark.unit
class TestPipelineRunnerServiceRun:
    """Test PipelineRunnerService.run method."""

    @pytest.mark.asyncio
    async def test_successful_run(
        self, service, mock_runner_factory, mock_runner, mock_metrics_extractor
    ):
        """Test successful pipeline execution."""
        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.SUCCESS
        assert result.pipeline_name == "test_pipeline"
        assert result.manifest_id == "manifest-123"
        assert result.records_fetched == 100
        assert result.records_silver == 90
        assert result.records_filtered_out == 7
        mock_runner_factory.contains.assert_called_with("test_pipeline")
        mock_runner_factory.create.assert_called_once()
        mock_runner.run.assert_called_once()
        mock_metrics_extractor.extract_metrics.assert_called_once_with(mock_runner)

    @pytest.mark.asyncio
    async def test_run_with_options(self, service, mock_runner_factory):
        """Test run with custom options."""
        options = RunOptions(
            run_type="backfill",
            resume=True,
            limit=50,
            log_level="DEBUG",
        )

        result = await service.run("test_pipeline", options=options)

        assert result.status == PipelineRunResult.SUCCESS
        assert result.run_type == "backfill"
        # Verify context was built with correct options
        call_args = mock_runner_factory.create.call_args
        context = call_args[0][0]  # First positional arg is context
        assert context.run_type.value == "backfill"
        assert context.resume is True
        assert context.limit == 50

    @pytest.mark.asyncio
    async def test_run_with_run_id(self, service, mock_runner_factory):
        """Test run with explicit run_id."""
        run_id = uuid4()

        result = await service.run("test_pipeline", run_id=run_id)

        assert result.run_id == str(run_id)
        call_args = mock_runner_factory.create.call_args
        context = call_args[0][0]
        assert context.run_id == run_id

    @pytest.mark.asyncio
    async def test_dry_run(self, service, mock_runner_factory, mock_runner):
        """Test dry-run mode."""
        options = RunOptions(dry_run=True)

        result = await service.run("test_pipeline", options=options)

        assert result.status == PipelineRunResult.DRY_RUN
        assert result.is_success is True
        # Runner should not be created in dry-run mode
        mock_runner_factory.create.assert_not_called()
        mock_runner.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_not_found(self, service, mock_runner_factory):
        """Test handling of unknown pipeline."""
        mock_runner_factory.contains.return_value = False
        mock_runner_factory.list_pipelines.return_value = ["other_pipeline"]

        with pytest.raises(PipelineNotFoundError) as exc_info:
            await service.run("unknown_pipeline")

        assert exc_info.value.pipeline_name == "unknown_pipeline"
        assert "other_pipeline" in exc_info.value.available

    @pytest.mark.asyncio
    async def test_pipeline_shutdown(
        self, service, mock_runner, mock_metrics_extractor
    ):
        """Test graceful shutdown handling."""
        mock_runner.run.side_effect = PipelineShutdownError("Signal received")

        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.SHUTDOWN
        assert result.is_success is False
        # Metrics should still be extracted
        mock_metrics_extractor.extract_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_failure(self, service, mock_runner, mock_metrics_extractor):
        """Test exception handling."""
        mock_runner.run.side_effect = ValueError("Invalid configuration")

        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.FAILED
        assert result.error_message == "Invalid configuration"
        assert result.error_type == "ValueError"
        mock_metrics_extractor.extract_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_fails_before_execution_for_runner_without_metrics(
        self,
        service,
        mock_runner_factory,
        mock_metrics_extractor,
    ):
        """Test producer boundary rejects non-metrics-readable runners pre-run."""

        class MinimalRunner:
            shutdown_signal = None
            run_id = "run-123"
            called = False

            async def run(self) -> None:
                await asyncio.sleep(0)
                self.called = True

        runner = MinimalRunner()
        mock_runner_factory.create.return_value = runner

        with pytest.raises(TypeError, match="ExecutionMetricsRunnerPort"):
            await service.run("test_pipeline")

        assert runner.called is False
        mock_metrics_extractor.extract_metrics.assert_not_called()


@pytest.mark.unit
class TestPipelineRunnerServiceObservability:
    """Black-box coverage for runner service observability signals."""

    @pytest.mark.asyncio
    async def test_success_path_binds_run_context_and_logs_completion(
        self, service, mock_logger
    ) -> None:
        """Successful runs should emit start + completion signals via bound logger."""
        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.SUCCESS
        mock_logger.bind.assert_called_once()
        bind_kwargs = mock_logger.bind.call_args.kwargs
        assert bind_kwargs["pipeline"] == "test_pipeline"
        assert bind_kwargs["pipeline_name"] == "test_pipeline"
        assert bind_kwargs["run_id"] == result.run_id
        assert "manifest_id" not in bind_kwargs
        mock_logger.info.assert_any_call(
            "Starting pipeline run",
            run_type="incremental",
            dry_run=False,
            limit=None,
        )
        mock_logger.info.assert_any_call("Pipeline completed successfully")

    @pytest.mark.asyncio
    async def test_dry_run_logs_start_and_skip_execution_signal(
        self, service, mock_logger, mock_runner_factory
    ) -> None:
        """Dry-run branch should stay observable without constructing a runner."""
        result = await service.run("test_pipeline", dry_run=True)

        assert result.status == PipelineRunResult.DRY_RUN
        mock_runner_factory.create.assert_not_called()
        mock_logger.info.assert_any_call(
            "Starting pipeline run",
            run_type="incremental",
            dry_run=True,
            limit=None,
        )
        mock_logger.info.assert_any_call("Dry-run mode: no execution performed")

    @pytest.mark.asyncio
    async def test_shutdown_path_logs_warning_signal(
        self, service, mock_runner, mock_logger
    ) -> None:
        """Graceful shutdown should emit warning-level observability signal."""
        mock_runner.run.side_effect = PipelineShutdownError("Signal received")

        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.SHUTDOWN
        mock_logger.warning.assert_called_once_with("Pipeline was gracefully shut down")

    @pytest.mark.asyncio
    async def test_failure_path_logs_exception_with_error_type(
        self, service, mock_runner, mock_logger
    ) -> None:
        """Failure branch should emit exception signal with normalized error type."""
        mock_runner.run.side_effect = ValueError("Invalid configuration")

        result = await service.run("test_pipeline")

        assert result.status == PipelineRunResult.FAILED
        mock_logger.exception.assert_called_once_with(
            "Pipeline failed with exception",
            error_type="ValueError",
        )


# =============================================================================
# Test PipelineRunnerService helper methods
# =============================================================================


@pytest.mark.unit
class TestPipelineRunnerServiceHelpers:
    """Test PipelineRunnerService helper methods."""

    def test_list_pipelines(self, service, mock_runner_factory):
        """Test listing available pipelines."""
        result = service.list_pipelines()

        assert result == ["test_pipeline", "other_pipeline"]
        mock_runner_factory.list_pipelines.assert_called_once()

    def test_validate_pipeline_exists(self, service, mock_runner_factory):
        """Test validating existing pipeline."""
        result = service.validate_pipeline("test_pipeline")

        assert result is True
        mock_runner_factory.contains.assert_called_with("test_pipeline")

    def test_validate_pipeline_not_exists(self, service, mock_runner_factory):
        """Test validating non-existing pipeline."""
        mock_runner_factory.contains.return_value = False

        result = service.validate_pipeline("unknown")

        assert result is False


# =============================================================================
# Test RunOptions merging
# =============================================================================


@pytest.mark.unit
class TestRunOptionsMerging:
    """Test RunOptions merging logic."""

    @pytest.mark.asyncio
    async def test_merge_dry_run_flag(self, service):
        """Test merging dry_run flag from parameter."""
        result = await service.run("test_pipeline", dry_run=True)

        assert result.status == PipelineRunResult.DRY_RUN

    @pytest.mark.asyncio
    async def test_options_override_dry_run_flag(self, service, mock_runner):
        """Test that options takes precedence over dry_run flag."""
        options = RunOptions(dry_run=False)

        # dry_run=True in params, but options.dry_run=False
        result = await service.run("test_pipeline", dry_run=True, options=options)

        # Options should take precedence
        assert result.status == PipelineRunResult.SUCCESS
        mock_runner.run.assert_called_once()


# =============================================================================
# Test context building
# =============================================================================


@pytest.mark.unit
class TestContextBuilding:
    """Test PipelineRunContext building."""

    @pytest.mark.asyncio
    async def test_context_with_input_filter(self, service, mock_runner_factory):
        """Test context building with input filter."""
        options = RunOptions(
            input_csv="/path/to/ids.csv",
            filter_column="mol_id",
            filter_field="molecule_id",
        )

        await service.run("test_pipeline", options=options)

        call_args = mock_runner_factory.create.call_args
        context = call_args[0][0]
        assert context.input_filter.enabled is True
        assert context.input_filter.source_path == "/path/to/ids.csv"
        assert context.input_filter.column_name == "mol_id"
        assert context.input_filter.filter_field == "molecule_id"

    @pytest.mark.asyncio
    async def test_context_without_input_filter(self, service, mock_runner_factory):
        """Test context building without input filter."""
        options = RunOptions()

        await service.run("test_pipeline", options=options)

        call_args = mock_runner_factory.create.call_args
        context = call_args[0][0]
        assert context.input_filter.enabled is False

    @pytest.mark.asyncio
    async def test_context_with_vacuum_config(self, service, mock_runner_factory):
        """Test context building with vacuum config."""
        options = RunOptions(
            vacuum_after_run=True,
            vacuum_retention_days=14,
        )

        await service.run("test_pipeline", options=options)

        call_args = mock_runner_factory.create.call_args
        context = call_args[0][0]
        assert context.vacuum.enabled is True
        assert context.vacuum.retention_days == 14
