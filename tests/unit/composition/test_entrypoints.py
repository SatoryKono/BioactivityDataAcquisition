# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for composition/entrypoints.py.

Tests the unified pipeline execution interface including:
- RunOptions configuration
- RunResult metrics and status
- run_pipeline() execution flow

This is dedicated entrypoint-boundary coverage and may patch
``bioetl.composition._pipeline_execution`` directly.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from tests.helpers.deterministic_ids import (
    deterministic_uuid_from_callsite,
    deterministic_uuid_string_from_callsite,
)

import pytest

from bioetl.composition.entrypoints import (
    ArchiveOptions,
    RunOptions,
    RunResult,
    PipelineRunResult,
    VacuumOptions,
    build_pipeline_context,
)
from bioetl.domain.types import RunType
from tests.helpers.clock import FixedClock

CACHED_BRONZE_PATH = "test-output/bronze"
_FIXED_CONTEXT_TIME = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
_FIXED_CONTEXT_CLOCK = FixedClock(_FIXED_CONTEXT_TIME)


@pytest.mark.unit
class TestRunOptions:
    """Tests for RunOptions dataclass."""

    def test_run_options_default_values(self):
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

    def test_run_options_accepts_custom_values(self):
        """Test RunOptions with custom values."""
        options = RunOptions(
            run_type="rebuild",
            resume=True,
            limit=1000,
            input_csv="/path/to/ids.csv",
            filter_column="chembl_id",
            filter_field="molecule_id",
            dry_run=True,
            vacuum_after_run=True,
            vacuum_retention_days=14,
        )

        assert options.run_type == "rebuild"
        assert options.resume is True
        assert options.limit == 1000
        assert options.input_csv == "/path/to/ids.csv"
        assert options.filter_column == "chembl_id"
        assert options.filter_field == "molecule_id"
        assert options.dry_run is True
        assert options.vacuum_after_run is True
        assert options.vacuum_retention_days == 14

    def test_run_options__frozen__44ca60cc(self):
        """Test RunOptions is immutable."""
        options = RunOptions()
        with pytest.raises(AttributeError):
            options.run_type = "rebuild"  # type: ignore


@pytest.mark.unit
class TestVacuumOptions:
    """Tests for VacuumOptions dataclass."""

    def test_entrypoints_vacuum_options__default_values(self):
        """Test VacuumOptions defaults."""
        options = VacuumOptions()
        assert options.retention_days == 7
        assert options.dry_run is False

    def test_vacuum_options_accepts_custom_values(self):
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
class TestPipelineRunResult:
    """Tests for PipelineRunResult enum."""

    def test_values(self):
        """Test PipelineRunResult enum values."""
        assert PipelineRunResult.SUCCESS.value == "success"
        assert PipelineRunResult.SHUTDOWN.value == "shutdown"
        assert PipelineRunResult.FAILED.value == "failed"

    def test_is_str_enum(self):
        """Test PipelineRunResult inherits from str."""
        assert isinstance(PipelineRunResult.SUCCESS, str)
        assert PipelineRunResult.SUCCESS == "success"


@pytest.mark.unit
class TestRunResult:
    """Tests for RunResult dataclass."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample RunResult for testing."""
        started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC)
        return RunResult(
            status=PipelineRunResult.SUCCESS,
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
            status=PipelineRunResult.SUCCESS,
            pipeline_name="test",
            run_id="123",
            run_type="incremental",
        )
        assert result.status == PipelineRunResult.SUCCESS
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
        assert sample_result.duration_seconds == pytest.approx(300.0)  # 5 minutes

    def test_success_rate(self, sample_result):
        """Test success_rate property."""
        assert sample_result.success_rate == pytest.approx(0.95)

    def test_entrypoints_run_result__rate_zero_fetched__c8855e20(self):
        """Test success_rate with zero records fetched."""
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="test",
            run_id="123",
            run_type="incremental",
            records_fetched=0,
        )
        assert result.success_rate == pytest.approx(1.0)  # No records = 100% success

    def test_entrypoints_run_result__failed_result__0e916511(self):
        """Test RunResult with FAILED status."""
        result = RunResult(
            status=PipelineRunResult.FAILED,
            pipeline_name="test",
            run_id="123",
            run_type="rebuild",
            error_message="Connection timeout",
        )
        assert result.status == PipelineRunResult.FAILED
        assert result.error_message == "Connection timeout"

    def test_entrypoints_run_result__shutdown_result__c147353d(self):
        """Test RunResult with SHUTDOWN status."""
        result = RunResult(
            status=PipelineRunResult.SHUTDOWN,
            pipeline_name="test",
            run_id="123",
            run_type="backfill",
            records_fetched=500,
            records_silver=450,
        )
        assert result.status == PipelineRunResult.SHUTDOWN
        assert result.records_fetched == 500


@pytest.mark.unit
class TestBuildPipelineContext:
    """Tests for build_pipeline_context function."""

    def test_basic_context(self):
        """Test building context with default options."""
        options = RunOptions()
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.pipeline_name == "chembl_activity"
        assert ctx.run_type == RunType.INCREMENTAL
        assert ctx.resume is False
        assert ctx.limit is None
        assert ctx.dry_run is False
        assert isinstance(ctx.run_id, UUID)

    def test_context_with_rebuild(self):
        """Test building context with rebuild run type."""
        options = RunOptions(run_type="rebuild", limit=100)
        ctx = build_pipeline_context(
            "pubchem_compound",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.run_type == RunType.REBUILD
        assert ctx.limit == 100

    @pytest.mark.unit
    def test_context_propagates_required_persistence_profile(self):
        """Test building context with an explicit persistence profile."""
        options = RunOptions(required_persistence_profile="degraded_observable")
        ctx = build_pipeline_context(
            "chembl_publication",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.required_persistence_profile == "degraded_observable"

    def test_context_with_input_filter__test_build_pipeline_context_unit_composition_test_entrypoints_267(
        self,
    ):
        """Test building context with input filter."""
        options = RunOptions(
            input_csv="/path/to/ids.csv",
            filter_column="chembl_id",
            filter_field="molecule_id",
        )
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.input_filter.enabled is True
        assert ctx.input_filter.source_path == "/path/to/ids.csv"
        assert ctx.input_filter.column_name == "chembl_id"
        assert ctx.input_filter.filter_field == "molecule_id"

    def test_context_without_input_filter__test_build_pipeline_context_unit_composition_test_entrypoints_285(
        self,
    ):
        """Test building context without input filter."""
        options = RunOptions()
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.input_filter.enabled is False

    def test_context_with_vacuum_config__test_build_pipeline_context_unit_composition_test_entrypoints_296(
        self,
    ):
        """Test building context with vacuum configuration."""
        options = RunOptions(vacuum_after_run=True, vacuum_retention_days=14)
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.vacuum.enabled is True
        assert ctx.vacuum.retention_days == 14

    def test_context_vacuum_none_uses_yaml(self):
        """Test vacuum=None preserves tri-state for YAML merge."""
        options = RunOptions(vacuum_after_run=None)
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.vacuum.enabled is None  # Tri-state: use YAML default

    def test_context_rejects_exact_replay_without_cached_bronze_or_parentage(self):
        """Legacy entrypoint must preserve exact-replay guardrails."""
        options = RunOptions(exact_replay=True)

        with pytest.raises(
            ValueError,
            match="exact replay currently requires --use-cached-bronze or",
        ):
            build_pipeline_context(
                "chembl_activity",
                options,
                clock=_FIXED_CONTEXT_CLOCK,
            )

    def test_context_propagates_exact_replay_with_cached_bronze(self):
        """Legacy entrypoint should preserve replay intent when cache mode is enabled."""
        options = RunOptions(
            use_cached_bronze=True,
            cached_bronze_path=CACHED_BRONZE_PATH,
            cached_bronze_date="2026-03-12",
            exact_replay=True,
        )
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            run_id=deterministic_uuid_from_callsite("test_entrypoints"),
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.exact_replay is True
        assert ctx.cached_bronze.enabled is True
        assert ctx.cached_bronze.bronze_path == CACHED_BRONZE_PATH
        assert ctx.cached_bronze.bronze_date == "2026-03-12"

    def test_context_allows_exact_replay_with_parentage_and_no_cached_bronze(self):
        """Legacy entrypoint may defer exact-replay cache resolution to control-plane evidence."""
        options = RunOptions(
            replay_of_run_id=deterministic_uuid_string_from_callsite(
                "test_entrypoints"
            ),
            replay_of_manifest_id="manifest-parent",
            exact_replay=True,
        )
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            run_id=deterministic_uuid_from_callsite("test_entrypoints"),
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.exact_replay is True
        assert ctx.cached_bronze.enabled is False
        assert ctx.replay_of_manifest_id == "manifest-parent"

    def test_context_requires_explicit_run_identity_for_exact_replay(self):
        """Legacy entrypoint must not synthesize replay occurrence IDs implicitly."""
        options = RunOptions(
            use_cached_bronze=True,
            cached_bronze_path=CACHED_BRONZE_PATH,
            exact_replay=True,
        )

        with pytest.raises(
            ValueError,
            match="exact replay requires explicit run_id or run_id_factory",
        ):
            build_pipeline_context(
                "chembl_activity",
                options,
                clock=_FIXED_CONTEXT_CLOCK,
            )

    def test_context_propagates_occurrence_pinned_resume_selectors(self):
        """Legacy entrypoint must preserve explicit checkpoint occurrence selectors."""
        options = RunOptions(
            resume=True,
            resume_run_id=deterministic_uuid_string_from_callsite("test_entrypoints"),
            resume_manifest_id="manifest-resume-anchor",
        )
        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.resume is True
        assert ctx.resume_run_id == options.resume_run_id
        assert ctx.resume_manifest_id == "manifest-resume-anchor"

    def test_context_uses_injected_clock_for_started_at(self) -> None:
        options = RunOptions()

        ctx = build_pipeline_context(
            "chembl_activity",
            options,
            clock=_FIXED_CONTEXT_CLOCK,
        )

        assert ctx.started_at == _FIXED_CONTEXT_TIME


@pytest.mark.unit
class TestCompositeBootstrapFacade:
    """Tests for composite bootstrap helpers exposed via entrypoints."""

    def test_entrypoints_reexport_composite_bootstrap_helpers(self) -> None:
        """Composite CLI should use entrypoints instead of runtime bootstrap module."""
        from bioetl.composition import entrypoints as composition_entrypoints
        from bioetl.composition.composite_api import (
            bootstrap_composite_runner as bootstrap_composite_runner_impl,
            load_composite_config as load_composite_config_impl,
        )

        assert (
            composition_entrypoints.bootstrap_composite_runner
            is bootstrap_composite_runner_impl
        )
        assert (
            composition_entrypoints.load_composite_config is load_composite_config_impl
        )

    def test_create_pipeline_runner_rejects_implicit_exact_replay_run_id(self) -> None:
        """Exact replay must fail closed at the public entrypoint when run_id is absent."""
        from bioetl.composition.entrypoints import create_pipeline_runner

        options = RunOptions(
            use_cached_bronze=True,
            cached_bronze_path=CACHED_BRONZE_PATH,
            exact_replay=True,
        )

        with pytest.raises(
            ValueError,
            match="exact replay requires explicit run_id or run_id_factory",
        ):
            create_pipeline_runner("chembl_activity", options)


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
        runner.run_id = deterministic_uuid_string_from_callsite("test_entrypoints")
        runner.shutdown_signal = None
        runner.execution_metrics = {
            "records_fetched": 100,
            "records_bronze": 100,
            "records_silver": 95,
            "records_gold": 90,
            "records_quarantined": 5,
        }
        return runner

    @pytest.fixture(autouse=True)
    def _mock_settings(self):
        """Mock get_settings and metrics server to avoid real config loading."""
        mock_settings = MagicMock()
        with (
            patch(
                "bioetl.composition._pipeline_execution.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.composition._pipeline_execution.maybe_start_metrics_server",
            ),
        ):
            yield

    @pytest.mark.asyncio
    async def test_run_pipeline_success(self, mock_runner):
        """Test run_pipeline returns success result."""
        from bioetl.composition.entrypoints import run_pipeline

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.SUCCESS
        assert result.pipeline_name == "test_pipeline"
        assert result.run_type == "incremental"
        assert result.records_fetched == 100
        assert result.records_silver == 95
        assert result.records_quarantined == 5
        assert result.error_message is None
        mock_push.assert_called_once_with(
            run_label="bioetl",
            pipeline_name="test_pipeline",
            run_type="incremental",
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_shutdown(self, mock_runner):
        """Test run_pipeline handles shutdown gracefully."""
        from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
        from bioetl.composition.entrypoints import run_pipeline

        mock_runner.run = AsyncMock(
            side_effect=PipelineShutdownError("Shutdown requested")
        )

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.SHUTDOWN
        assert result.error_message is None  # Shutdown is not an error
        mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_pipeline_failure(self, mock_runner):
        """Test run_pipeline handles failures."""
        from bioetl.composition.entrypoints import run_pipeline

        mock_runner.run = AsyncMock(side_effect=RuntimeError("Connection failed"))

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions(run_type="rebuild"))

        assert result.status == PipelineRunResult.FAILED
        assert result.error_message == "Connection failed"
        assert result.run_type == "rebuild"
        mock_push.assert_called_once_with(
            run_label="bioetl",
            pipeline_name="test_pipeline",
            run_type="rebuild",
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_preserves_metrics_on_failure(self, mock_runner):
        """Test run_pipeline preserves partial metrics on failure."""
        from bioetl.composition.entrypoints import run_pipeline

        # Simulate partial processing before failure
        mock_runner.execution_metrics["records_fetched"] = 50
        mock_runner.execution_metrics["records_silver"] = 45
        mock_runner.run = AsyncMock(side_effect=RuntimeError("Mid-run failure"))

        with patch(
            "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
            return_value=mock_runner,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.FAILED
        assert result.records_fetched == 50
        assert result.records_silver == 45

    @pytest.mark.asyncio
    async def test_run_pipeline_calculates_duration(self, mock_runner):
        """Test run_pipeline tracks execution duration."""
        from bioetl.composition.entrypoints import run_pipeline

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ),
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.duration_seconds >= 0
        assert result.started_at <= result.completed_at

    @pytest.mark.asyncio
    async def test_run_pipeline_ignores_pushgateway_failure(self, mock_runner):
        """Best-effort metrics publication must not fail the pipeline."""
        from bioetl.composition.entrypoints import run_pipeline

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=False,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.SUCCESS
        mock_push.assert_called_once()

    @pytest.mark.parametrize(
        ("run_side_effect", "expected_status"),
        [
            (None, PipelineRunResult.SUCCESS),
            (RuntimeError("short-lived failure"), PipelineRunResult.FAILED),
        ],
    )
    @pytest.mark.asyncio
    async def test_run_pipeline_publishes_terminal_metrics_for_short_lived_runs(
        self,
        mock_runner,
        run_side_effect: Exception | None,
        expected_status: PipelineRunResult,
    ):
        """Short-lived completion paths must still flush terminal metrics."""
        from bioetl.composition.entrypoints import run_pipeline

        if run_side_effect is not None:
            mock_runner.run = AsyncMock(side_effect=run_side_effect)

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions(run_type="rebuild"))

        assert result.status == expected_status
        mock_push.assert_called_once_with(
            run_label="bioetl",
            pipeline_name="test_pipeline",
            run_type="rebuild",
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_requires_metrics_readable_runner(self):
        """Bootstrap contract failures return a structured failed run result."""
        from bioetl.composition.entrypoints import run_pipeline

        class MinimalRunner:
            run_id = "run-123"
            shutdown_signal = None
            called = False

            async def run(self):
                await asyncio.sleep(0)
                self.called = True
                return None

        runner = MinimalRunner()
        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions(run_type="rebuild"))

        assert result.status == PipelineRunResult.FAILED
        assert result.error_type == "TypeError"
        assert "ExecutionMetricsRunnerPort" in (result.error_message or "")
        assert result.run_type == "rebuild"
        assert result.records_fetched == 0
        mock_push.assert_called_once_with(
            run_label="bioetl",
            pipeline_name="test_pipeline",
            run_type="rebuild",
        )
        assert runner.called is False

    @pytest.mark.asyncio
    async def test_run_pipeline_publishes_terminal_metrics_for_bootstrap_failure(self):
        """Config/DI bootstrap failures still publish terminal metrics best-effort."""
        from bioetl.composition.entrypoints import run_pipeline

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                side_effect=ValueError("invalid pipeline config"),
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ) as mock_push,
        ):
            result = await run_pipeline("test_pipeline", RunOptions(run_type="rebuild"))

        assert result.status == PipelineRunResult.FAILED
        assert result.error_message == "invalid pipeline config"
        assert result.error_type == "ValueError"
        assert UUID(result.run_id)
        mock_push.assert_called_once_with(
            run_label="bioetl",
            pipeline_name="test_pipeline",
            run_type="rebuild",
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_rejects_implicit_exact_replay_run_id(self) -> None:
        """Exact replay must fail before bootstrap when no explicit occurrence ID exists."""
        from bioetl.composition.entrypoints import run_pipeline

        options = RunOptions(
            use_cached_bronze=True,
            cached_bronze_path=CACHED_BRONZE_PATH,
            exact_replay=True,
        )

        with pytest.raises(
            ValueError,
            match="exact replay requires explicit run_id or run_id_factory",
        ):
            await run_pipeline("chembl_activity", options)

    @pytest.mark.asyncio
    async def test_run_pipeline_preserves_context_run_id_even_if_runner_exposes_another(
        self, mock_runner
    ):
        """Entry-point result identity must come from the prepared execution context."""
        from bioetl.composition.entrypoints import run_pipeline

        runner_run_id = deterministic_uuid_string_from_callsite("test_entrypoints")
        mock_runner.run_id = runner_run_id

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ),
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.SUCCESS
        assert result.run_id != runner_run_id
        assert UUID(result.run_id)

    @pytest.mark.asyncio
    async def test_run_pipeline_does_not_start_metrics_server_directly(
        self, mock_runner
    ):
        """Runtime side effects must stay at the outer CLI/runtime boundary."""
        from bioetl.composition.entrypoints import run_pipeline

        with (
            patch(
                "bioetl.composition._pipeline_execution._create_pipeline_runner_from_context",
                return_value=mock_runner,
            ),
            patch(
                "bioetl.composition._pipeline_execution.maybe_start_metrics_server",
            ) as mock_start_metrics,
            patch(
                "bioetl.composition._pipeline_execution.push_metrics_to_gateway",
                return_value=True,
            ),
        ):
            result = await run_pipeline("test_pipeline", RunOptions())

        assert result.status == PipelineRunResult.SUCCESS
        mock_start_metrics.assert_not_called()
