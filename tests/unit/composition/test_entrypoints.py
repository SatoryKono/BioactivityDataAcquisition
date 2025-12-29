"""Unit tests for composition/entrypoints.py.

Tests the unified pipeline execution interface including:
- RunOptions configuration
- RunResult metrics and status
- run_pipeline() execution flow
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from bioetl.composition.entrypoints import (
    ArchiveOptions,
    RunOptions,
    RunResult,
    RunStatus,
    VacuumOptions,
    build_pipeline_context,
)
from bioetl.domain.types import RunType


@pytest.mark.unit
class TestRunOptions:
    """Tests for RunOptions dataclass."""

    def test_default_values(self):
        """Test RunOptions has sensible defaults."""
        options = RunOptions()

        assert options.run_type == "incremental"
        assert options.resume is False
        assert options.limit is None
        assert options.input_csv is None
        assert options.filter_column is None
        assert options.filter_field is None
        assert options.dry_run is False
        assert options.vacuum_after_run is None
        assert options.vacuum_retention_days is None

    def test_custom_values(self):
        """Test RunOptions with custom values."""
        options = RunOptions(
            run_type="rebuild",
            resume=True,
            limit=1000,
            input_csv="/path/to/ids.csv",
            filter_column="chembl_id",
            filter_field="molecule_chembl_id",
            dry_run=True,
            vacuum_after_run=True,
            vacuum_retention_days=14,
        )

        assert options.run_type == "rebuild"
        assert options.resume is True
        assert options.limit == 1000
        assert options.input_csv == "/path/to/ids.csv"
        assert options.filter_column == "chembl_id"
        assert options.filter_field == "molecule_chembl_id"
        assert options.dry_run is True
        assert options.vacuum_after_run is True
        assert options.vacuum_retention_days == 14

    def test_frozen(self):
        """Test RunOptions is immutable."""
        options = RunOptions()
        with pytest.raises(AttributeError):
            options.run_type = "rebuild"  # type: ignore


@pytest.mark.unit
class TestVacuumOptions:
    """Tests for VacuumOptions dataclass."""

    def test_default_values(self):
        """Test VacuumOptions defaults."""
        options = VacuumOptions()
        assert options.retention_days == 7
        assert options.dry_run is False

    def test_custom_values(self):
        """Test VacuumOptions with custom values."""
        options = VacuumOptions(retention_days=30, dry_run=True)
        assert options.retention_days == 30
        assert options.dry_run is True


@pytest.mark.unit
class TestArchiveOptions:
    """Tests for ArchiveOptions dataclass."""

    def test_required_target_path(self):
        """Test ArchiveOptions requires target_path."""
        options = ArchiveOptions(target_path="/archive/data")
        assert options.target_path == "/archive/data"
        assert options.remove_source is False

    def test_with_remove_source(self):
        """Test ArchiveOptions with remove_source."""
        options = ArchiveOptions(target_path="/archive", remove_source=True)
        assert options.remove_source is True


@pytest.mark.unit
class TestRunStatus:
    """Tests for RunStatus enum."""

    def test_values(self):
        """Test RunStatus enum values."""
        assert RunStatus.SUCCESS.value == "success"
        assert RunStatus.SHUTDOWN.value == "shutdown"
        assert RunStatus.FAILED.value == "failed"

    def test_is_str_enum(self):
        """Test RunStatus inherits from str."""
        assert isinstance(RunStatus.SUCCESS, str)
        assert RunStatus.SUCCESS == "success"


@pytest.mark.unit
class TestRunResult:
    """Tests for RunResult dataclass."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample RunResult for testing."""
        started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC)
        return RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="abc-123",
            run_type="incremental",
            records_fetched=1000,
            records_bronze=1000,
            records_silver=950,
            records_gold=900,
            records_quarantined=50,
            started_at=started,
            completed_at=completed,
        )

    def test_required_fields(self):
        """Test RunResult with required fields only."""
        result = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="test",
            run_id="123",
            run_type="incremental",
        )
        assert result.status == RunStatus.SUCCESS
        assert result.pipeline_name == "test"
        assert result.run_id == "123"
        assert result.run_type == "incremental"
        # Defaults
        assert result.records_fetched == 0
        assert result.records_bronze == 0
        assert result.records_silver == 0
        assert result.records_gold == 0
        assert result.records_quarantined == 0
        assert result.error_message is None

    def test_duration_seconds(self, sample_result):
        """Test duration_seconds property."""
        assert sample_result.duration_seconds == 300.0  # 5 minutes

    def test_success_rate(self, sample_result):
        """Test success_rate property."""
        # (1000 - 50) / 1000 = 0.95
        assert sample_result.success_rate == 0.95

    def test_success_rate_zero_fetched(self):
        """Test success_rate with zero records fetched."""
        result = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="test",
            run_id="123",
            run_type="incremental",
            records_fetched=0,
        )
        assert result.success_rate == 1.0  # No records = 100% success

    def test_failed_result(self):
        """Test RunResult with FAILED status."""
        result = RunResult(
            status=RunStatus.FAILED,
            pipeline_name="test",
            run_id="123",
            run_type="rebuild",
            error_message="Connection timeout",
        )
        assert result.status == RunStatus.FAILED
        assert result.error_message == "Connection timeout"

    def test_shutdown_result(self):
        """Test RunResult with SHUTDOWN status."""
        result = RunResult(
            status=RunStatus.SHUTDOWN,
            pipeline_name="test",
            run_id="123",
            run_type="backfill",
            records_fetched=500,
            records_silver=450,
        )
        assert result.status == RunStatus.SHUTDOWN
        assert result.records_fetched == 500


@pytest.mark.unit
class TestBuildPipelineContext:
    """Tests for build_pipeline_context function."""

    def test_basic_context(self):
        """Test building context with default options."""
        options = RunOptions()
        ctx = build_pipeline_context("chembl_activity", options)

        assert ctx.pipeline_name == "chembl_activity"
        assert ctx.run_type == RunType.INCREMENTAL
        assert ctx.resume is False
        assert ctx.limit is None
        assert ctx.dry_run is False
        assert isinstance(ctx.run_id, UUID)

    def test_context_with_rebuild(self):
        """Test building context with rebuild run type."""
        options = RunOptions(run_type="rebuild", limit=100)
        ctx = build_pipeline_context("pubchem_compound", options)

        assert ctx.run_type == RunType.REBUILD
        assert ctx.limit == 100

    def test_context_with_input_filter(self):
        """Test building context with input filter."""
        options = RunOptions(
            input_csv="/path/to/ids.csv",
            filter_column="chembl_id",
            filter_field="molecule_chembl_id",
        )
        ctx = build_pipeline_context("chembl_activity", options)

        assert ctx.input_filter.enabled is True
        assert ctx.input_filter.source_path == "/path/to/ids.csv"
        assert ctx.input_filter.column_name == "chembl_id"
        assert ctx.input_filter.filter_field == "molecule_chembl_id"

    def test_context_without_input_filter(self):
        """Test building context without input filter."""
        options = RunOptions()
        ctx = build_pipeline_context("chembl_activity", options)

        assert ctx.input_filter.enabled is False

    def test_context_with_vacuum_config(self):
        """Test building context with vacuum configuration."""
        options = RunOptions(vacuum_after_run=True, vacuum_retention_days=14)
        ctx = build_pipeline_context("chembl_activity", options)

        assert ctx.vacuum.enabled is True
        assert ctx.vacuum.retention_days == 14

    def test_context_vacuum_none_uses_yaml(self):
        """Test vacuum=None preserves tri-state for YAML merge."""
        options = RunOptions(vacuum_after_run=None)
        ctx = build_pipeline_context("chembl_activity", options)

        assert ctx.vacuum.enabled is None  # Tri-state: use YAML default


@pytest.mark.unit
class TestRunPipelineIntegration:
    """Integration-style tests for run_pipeline function.

    These tests mock the runner to verify the control flow.
    """

    @pytest.fixture
    def mock_runner(self):
        """Create a mock PipelineRunner."""
        runner = MagicMock()
        runner.run = AsyncMock()
        runner._context = MagicMock()
        runner._context.run_id = uuid4()
        runner._executor = MagicMock()
        runner._executor.records_fetched = 100
        runner._executor.records_bronze = 100
        runner._executor.records_silver = 95
        runner._executor.records_gold = 90
        runner._executor.records_quarantined = 5
        return runner

    @pytest.mark.asyncio
    async def test_run_pipeline_success(self, mock_runner):
        """Test run_pipeline returns success result."""
        from bioetl.composition.entrypoints import run_pipeline

        with patch(
            "bioetl.composition.entrypoints.create_pipeline_runner",
            return_value=mock_runner,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == RunStatus.SUCCESS
        assert result.pipeline_name == "test_pipeline"
        assert result.run_type == "incremental"
        assert result.records_fetched == 100
        assert result.records_silver == 95
        assert result.records_quarantined == 5
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_run_pipeline_shutdown(self, mock_runner):
        """Test run_pipeline handles shutdown gracefully."""
        from bioetl.application.core.shutdown import PipelineShutdownError
        from bioetl.composition.entrypoints import run_pipeline

        mock_runner.run = AsyncMock(
            side_effect=PipelineShutdownError("Shutdown requested")
        )

        with patch(
            "bioetl.composition.entrypoints.create_pipeline_runner",
            return_value=mock_runner,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == RunStatus.SHUTDOWN
        assert result.error_message is None  # Shutdown is not an error

    @pytest.mark.asyncio
    async def test_run_pipeline_failure(self, mock_runner):
        """Test run_pipeline handles failures."""
        from bioetl.composition.entrypoints import run_pipeline

        mock_runner.run = AsyncMock(side_effect=RuntimeError("Connection failed"))

        with patch(
            "bioetl.composition.entrypoints.create_pipeline_runner",
            return_value=mock_runner,
        ):
            result = await run_pipeline(
                "test_pipeline", RunOptions(run_type="rebuild")
            )

        assert result.status == RunStatus.FAILED
        assert result.error_message == "Connection failed"
        assert result.run_type == "rebuild"

    @pytest.mark.asyncio
    async def test_run_pipeline_preserves_metrics_on_failure(self, mock_runner):
        """Test run_pipeline preserves partial metrics on failure."""
        from bioetl.composition.entrypoints import run_pipeline

        # Simulate partial processing before failure
        mock_runner._executor.records_fetched = 50
        mock_runner._executor.records_silver = 45
        mock_runner.run = AsyncMock(side_effect=RuntimeError("Mid-run failure"))

        with patch(
            "bioetl.composition.entrypoints.create_pipeline_runner",
            return_value=mock_runner,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == RunStatus.FAILED
        assert result.records_fetched == 50
        assert result.records_silver == 45

    @pytest.mark.asyncio
    async def test_run_pipeline_calculates_duration(self, mock_runner):
        """Test run_pipeline tracks execution duration."""
        from bioetl.composition.entrypoints import run_pipeline

        with patch(
            "bioetl.composition.entrypoints.create_pipeline_runner",
            return_value=mock_runner,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.duration_seconds >= 0
        assert result.started_at <= result.completed_at
