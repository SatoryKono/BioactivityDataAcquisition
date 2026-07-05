"""Tests for dependency state-transition helpers in composite runner orchestration."""

from __future__ import annotations

import pytest

from bioetl.application.composite.runner_pkg.runner_stage_dependency_state_flow import (
    complete_dependencies_phase,
    handle_dependencies_phase_exception,
    start_dependencies_phase,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError


class TestStartDependenciesPhase:
    """Tests for start_dependencies_phase function."""

    @pytest.mark.asyncio
    async def test_transitions_to_dependencies_running(self, mock_host, mock_state):
        """Should transition state to DEPENDENCIES_RUNNING."""
        result = await start_dependencies_phase(
            mock_host,
            mock_state,
            dependency_pipeline_names=["dep1", "dep2"],
        )
        assert result.state == CompositePipelineState.DEPENDENCIES_RUNNING

    @pytest.mark.asyncio
    async def test_calls_host_record_dependencies_stage_started(
        self, mock_host, mock_state
    ):
        """Should call host._record_dependencies_stage_started with pipeline names."""
        await start_dependencies_phase(
            mock_host,
            mock_state,
            dependency_pipeline_names=["dep1", "dep2"],
        )
        mock_host._record_dependencies_stage_started.assert_called_once_with(
            ["dep1", "dep2"]
        )


class TestCompleteDependenciesPhase:
    """Tests for complete_dependencies_phase function."""

    @pytest.mark.asyncio
    async def test_transitions_to_dependencies_completed(self, mock_host, mock_state):
        """Should transition state to DEPENDENCIES_COMPLETED."""
        result = await complete_dependencies_phase(
            mock_host,
            mock_state,
            succeeded=5,
            failed=0,
        )
        assert result.state == CompositePipelineState.DEPENDENCIES_COMPLETED

    @pytest.mark.asyncio
    async def test_emits_phase_completed_with_details(self, mock_host, mock_state):
        """Should emit phase_completed event with succeeded/failed counts."""
        await complete_dependencies_phase(
            mock_host,
            mock_state,
            succeeded=5,
            failed=2,
        )
        mock_host._observer.emit_phase_completed.assert_called_once()
        call_kwargs = mock_host._observer.emit_phase_completed.call_args.kwargs
        assert call_kwargs["phase_name"] == "dependencies"
        assert call_kwargs["details"]["succeeded"] == 5
        assert call_kwargs["details"]["failed"] == 2

    @pytest.mark.asyncio
    async def test_saves_checkpoint(self, mock_host, mock_state):
        """Should call save_checkpoint with dependencies_completed operation."""
        await complete_dependencies_phase(
            mock_host,
            mock_state,
            succeeded=5,
            failed=0,
        )
        mock_host._call_save_checkpoint_safe.assert_called_once()


class TestHandleDependenciesPhaseException:
    """Tests for handle_dependencies_phase_exception function."""

    @pytest.mark.asyncio
    async def test_logs_error_with_composite_and_run_id(self, mock_host, mock_state):
        """Should log error with composite name and run_id."""
        error = ValueError("test error")
        await handle_dependencies_phase_exception(mock_host, mock_state, error)
        mock_host._logger.error.assert_called_once()
        call_kwargs = mock_host._logger.error.call_args.kwargs
        assert "composite" in call_kwargs
        assert "run_id" in call_kwargs
        assert "error" in call_kwargs

    @pytest.mark.asyncio
    async def test_includes_reason_code_for_bioetl_error(self, mock_host, mock_state):
        """Should include reason_code when error is BioETLError."""
        error = BioETLError("test bioetl error", reason_code="test_reason")
        await handle_dependencies_phase_exception(mock_host, mock_state, error)
        mock_host._logger.error.assert_called_once()
        call_kwargs = mock_host._logger.error.call_args.kwargs
        assert call_kwargs.get("reason_code") == "test_reason"

    @pytest.mark.asyncio
    async def test_persists_failed_state(self, mock_host, mock_state):
        """Should persist failed state with error details."""
        error = ValueError("test error")
        await handle_dependencies_phase_exception(mock_host, mock_state, error)
        mock_host._persist_failed_state.assert_called_once()
        call_kwargs = mock_host._persist_failed_state.call_args.kwargs
        assert call_kwargs["stage"] == "dependencies_failed"
        assert call_kwargs["error"] == "test error"
