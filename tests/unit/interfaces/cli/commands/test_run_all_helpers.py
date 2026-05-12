"""Unit tests for canonical run-all support helper functions.

Tests batch run utilities including registry resolution, provider filtering,
execution plan creation, result recording, and summary output.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    create_run_all_options,
    echo_batch_summary,
    filter_pipelines_by_provider,
    get_available_providers,
    handle_destructive_confirmation,
    record_pipeline_failure,
    record_pipeline_result,
    resolve_run_all_registry,
    resolve_run_all_execution_plan,
    should_prompt_for_destructive_run,
    validate_provider,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

_PIPELINES = [
    "chembl_activity",
    "chembl_molecule",
    "pubchem_compound",
    "uniprot_protein",
]


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock registry with standard pipelines."""
    registry = MagicMock()
    registry.list_pipelines.return_value = _PIPELINES
    return registry


@pytest.mark.unit
class TestResolveRunAllRegistry:
    """Tests for resolve_run_all_registry helper."""

    def test_returns_explicit_registry(self, mock_registry: MagicMock) -> None:
        """Test that an explicitly provided registry is returned directly."""
        result = resolve_run_all_registry(mock_registry)
        assert result is mock_registry

    def test_raises_when_no_registry_available(self) -> None:
        """Test RuntimeError is raised when no registry is available."""
        with patch("click.get_current_context", return_value=None):
            with pytest.raises(
                RuntimeError, match="require an explicit PipelineRegistry"
            ):
                resolve_run_all_registry(None)


@pytest.mark.unit
class TestGetAvailableProviders:
    """Tests for get_available_providers helper."""

    def test_returns_sorted_unique_providers(self, mock_registry: MagicMock) -> None:
        """Test that unique providers are extracted, sorted, from pipeline names."""
        result = get_available_providers(mock_registry)

        assert result == ["chembl", "pubchem", "uniprot"]

    def test_empty_registry_returns_empty_list(self) -> None:
        """Test that empty registry yields empty provider list."""
        registry = MagicMock()
        registry.list_pipelines.return_value = []

        result = get_available_providers(registry)

        assert result == []


@pytest.mark.unit
class TestFilterPipelinesByProvider:
    """Tests for filter_pipelines_by_provider helper."""

    def test_filters_by_chembl_prefix(self, mock_registry: MagicMock) -> None:
        """Test filtering pipelines with chembl prefix."""
        result = filter_pipelines_by_provider("chembl", mock_registry)

        assert result == ["chembl_activity", "chembl_molecule"]

    def test_unknown_provider_returns_empty_list(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that an unregistered provider prefix returns empty list."""
        result = filter_pipelines_by_provider("nonexistent", mock_registry)

        assert result == []


@pytest.mark.unit
class TestValidateProvider:
    """Tests for validate_provider helper."""

    def test_valid_provider_returns_true_no_error(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that a registered provider returns (True, None)."""
        ok, error = validate_provider("chembl", registry=mock_registry)

        assert ok is True
        assert error is None

    def test_invalid_provider_returns_false_with_error(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that unknown provider returns (False, error_message)."""
        ok, error = validate_provider("unknown_provider", registry=mock_registry)

        assert ok is False
        assert error is not None
        assert "unknown_provider" in error

    def test_empty_registry_returns_false(self) -> None:
        """Test that empty registry yields no-pipelines error."""
        registry = MagicMock()
        registry.list_pipelines.return_value = []

        ok, error = validate_provider("chembl", registry=registry)

        assert ok is False
        assert error is not None


@pytest.mark.unit
class TestCreateRunAllOptions:
    """Tests for create_run_all_options helper."""

    def test_creates_options_with_debug_log_level(self) -> None:
        """Test that debug=True sets log_level to DEBUG."""
        options = create_run_all_options(
            run_type="incremental",
            limit=None,
            dry_run=False,
            debug=True,
        )

        assert options.log_level == "DEBUG"

    def test_creates_options_with_info_log_level(self) -> None:
        """Test that debug=False sets log_level to INFO."""
        options = create_run_all_options(
            run_type="incremental",
            limit=100,
            dry_run=True,
            debug=False,
        )

        assert options.log_level == "INFO"
        assert options.limit == 100
        assert options.dry_run is True


@pytest.mark.unit
class TestResolveRunAllExecutionPlan:
    """Tests for resolve_run_all_execution_plan helper."""

    def test_valid_provider_returns_plan(self, mock_registry: MagicMock) -> None:
        """Test that a valid provider returns a populated RunAllExecutionPlan."""
        plan, error = resolve_run_all_execution_plan(
            source="chembl",
            run_type="incremental",
            limit=None,
            dry_run=False,
            debug=False,
            registry=mock_registry,
        )

        assert plan is not None
        assert error is None
        assert "chembl_activity" in plan.pipelines
        assert "chembl_molecule" in plan.pipelines

    def test_invalid_provider_returns_none_with_error(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that an invalid provider returns (None, error_message)."""
        plan, error = resolve_run_all_execution_plan(
            source="bad_provider",
            run_type="incremental",
            limit=None,
            dry_run=False,
            debug=False,
            registry=mock_registry,
        )

        assert plan is None
        assert error is not None


@pytest.mark.unit
class TestShouldPromptForDestructiveRun:
    """Tests for should_prompt_for_destructive_run helper."""

    @pytest.mark.parametrize(
        ("run_type", "dry_run", "yes", "expected"),
        [
            ("incremental", False, False, False),
            ("rebuild", True, False, False),
            ("rebuild", False, True, False),
            ("rebuild", False, False, True),
            ("backfill", False, False, True),
        ],
    )
    def test_prompt_conditions(
        self,
        run_type: str,
        dry_run: bool,
        yes: bool,
        expected: bool,
    ) -> None:
        """Test all conditions for prompting before destructive runs."""
        result = should_prompt_for_destructive_run(
            run_type=run_type, dry_run=dry_run, yes=yes
        )
        assert result is expected


@pytest.mark.unit
class TestHandleDestructiveConfirmation:
    """Tests for handle_destructive_confirmation helper."""

    def test_incremental_returns_true_without_prompt(self) -> None:
        """Test incremental run skips confirmation and returns True."""
        mock_confirm = MagicMock()

        result = handle_destructive_confirmation(
            run_type="incremental",
            pipelines=["chembl_activity"],
            dry_run=False,
            yes=False,
            confirm_fn=mock_confirm,
        )

        assert result is True
        mock_confirm.assert_not_called()

    def test_rebuild_confirmed_returns_true(self) -> None:
        """Test confirmed rebuild returns True."""
        mock_confirm = MagicMock(return_value=True)
        mock_info = MagicMock()

        result = handle_destructive_confirmation(
            run_type="rebuild",
            pipelines=["chembl_activity"],
            dry_run=False,
            yes=False,
            confirm_fn=mock_confirm,
            info_printer=mock_info,
        )

        assert result is True

    def test_rebuild_denied_calls_exit(self) -> None:
        """Test that denied rebuild calls exit function."""
        mock_confirm = MagicMock(return_value=False)
        mock_exit = MagicMock()
        mock_info = MagicMock()

        handle_destructive_confirmation(
            run_type="rebuild",
            pipelines=["chembl_activity"],
            dry_run=False,
            yes=False,
            confirm_fn=mock_confirm,
            info_printer=mock_info,
            exit_func=mock_exit,
        )

        mock_exit.assert_called_once_with(ExitCode.OK)


@pytest.mark.unit
class TestRecordPipelineResult:
    """Tests for record_pipeline_result helper."""

    def test_success_increments_succeeded(self) -> None:
        """Test SUCCESS result increments succeeded counter."""
        batch = BatchRunResult(total=1)
        result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="run-1",
            run_type="incremental",
        )

        should_stop = record_pipeline_result(
            batch_result=batch, pipeline="chembl_activity", result=result
        )

        assert batch.succeeded == 1
        assert should_stop is False

    def test_dry_run_increments_skipped(self) -> None:
        """Test DRY_RUN result increments skipped counter."""
        batch = BatchRunResult(total=1)
        result = RunResult(
            status=PipelineRunResult.DRY_RUN,
            pipeline_name="chembl_activity",
            run_id="run-1",
            run_type="incremental",
        )

        should_stop = record_pipeline_result(
            batch_result=batch, pipeline="chembl_activity", result=result
        )

        assert batch.skipped == 1
        assert should_stop is False

    def test_shutdown_increments_skipped_and_stops(self) -> None:
        """Test SHUTDOWN result increments skipped and signals stop."""
        batch = BatchRunResult(total=1)
        result = RunResult(
            status=PipelineRunResult.SHUTDOWN,
            pipeline_name="chembl_activity",
            run_id="run-1",
            run_type="incremental",
        )

        should_stop = record_pipeline_result(
            batch_result=batch, pipeline="chembl_activity", result=result
        )

        assert batch.skipped == 1
        assert should_stop is True

    def test_failed_increments_failed(self) -> None:
        """Test FAILED result increments failed and records pipeline name."""
        batch = BatchRunResult(total=1)
        result = RunResult(
            status=PipelineRunResult.FAILED,
            pipeline_name="chembl_activity",
            run_id="run-1",
            run_type="incremental",
            error_message="timeout",
        )

        should_stop = record_pipeline_result(
            batch_result=batch, pipeline="chembl_activity", result=result
        )

        assert batch.failed == 1
        assert "chembl_activity" in batch.failed_pipelines
        assert should_stop is False


@pytest.mark.unit
class TestRecordPipelineFailure:
    """Tests for record_pipeline_failure helper."""

    def test_increments_failed_and_appends_name(self) -> None:
        """Test that failure is recorded and pipeline name is tracked."""
        batch = BatchRunResult(total=1)

        record_pipeline_failure(
            batch_result=batch,
            pipeline="chembl_activity",
            title="[FAIL] chembl_activity: failed",
            detail="timeout after 30s",
        )

        assert batch.failed == 1
        assert "chembl_activity" in batch.failed_pipelines


@pytest.mark.unit
class TestEchoBatchSummary:
    """Tests for echo_batch_summary helper."""

    def test_dry_run_summary(self) -> None:
        """Test dry-run summary uses preview language."""
        batch = BatchRunResult(total=3, succeeded=0, failed=0, skipped=3)
        messages: list[str] = []

        def info_printer(*args: str) -> None:
            messages.extend(args)

        echo_batch_summary(result=batch, dry_run=True, info_printer=info_printer)

        combined = " ".join(messages)
        assert "dry" in combined.lower() or "preview" in combined.lower()

    def test_failed_summary_calls_error_printer(self) -> None:
        """Test that failed pipelines are reported via error_printer."""
        batch = BatchRunResult(
            total=2,
            succeeded=1,
            failed=1,
            failed_pipelines=["chembl_activity"],
        )
        info_messages: list[str] = []
        error_messages: list[str] = []

        def _info_printer(*args: object) -> None:
            info_messages.extend(str(x) for x in args)

        def _error_printer(*args: object) -> None:
            error_messages.extend(str(x) for x in args)

        echo_batch_summary(
            result=batch,
            dry_run=False,
            info_printer=_info_printer,
            error_printer=_error_printer,
        )

        assert any("chembl_activity" in m for m in error_messages)
