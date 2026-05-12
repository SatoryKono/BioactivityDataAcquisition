"""Unit tests for canonical run support helper functions.

Tests validation, registry resolution, confirmation, and cleanup preview helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest

from bioetl.composition.registry_api import PipelineRegistry
from bioetl.interfaces.cli.commands.domains.run.support import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    resolve_context_registry,
    show_cleanup_preview,
    validate_pipeline_name,
)

_PIPELINES = ["chembl_activity", "chembl_molecule", "pubchem_compound"]


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock PipelineRegistry."""
    registry = MagicMock(spec=PipelineRegistry)
    registry.list_pipelines.return_value = _PIPELINES
    return registry


@pytest.mark.unit
class TestResolveContextRegistry:
    """Tests for resolve_context_registry helper."""

    def test_returns_none_when_no_context(self) -> None:
        """Test returns None outside of a Click context."""
        result = resolve_context_registry(None)
        assert result is None

    def test_returns_registry_from_context(self, mock_registry: MagicMock) -> None:
        """Test returns registry when context obj is a PipelineRegistry."""
        click_context = MagicMock(spec=click.Context)
        click_context.obj = mock_registry
        result = resolve_context_registry(click_context)
        assert result is mock_registry

    def test_returns_none_when_context_obj_is_not_registry(self) -> None:
        """Test returns None when context obj is not a PipelineRegistry."""
        click_context = MagicMock(spec=click.Context)
        click_context.obj = "not a registry"
        result = resolve_context_registry(click_context)
        assert result is None


@pytest.mark.unit
class TestValidatePipelineName:
    """Tests for validate_pipeline_name Click callback."""

    def test_valid_pipeline_returns_value(self, mock_registry: MagicMock) -> None:
        """Test that a valid pipeline name is returned unchanged."""
        with patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ):
            result = validate_pipeline_name(None, None, "chembl_activity")

        assert result == "chembl_activity"

    def test_invalid_pipeline_raises_bad_parameter(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that unknown pipeline raises click.BadParameter."""
        with patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ):
            with pytest.raises(click.BadParameter) as exc_info:
                validate_pipeline_name(None, None, "nonexistent_pipeline")

        assert "Unknown pipeline" in str(exc_info.value)

    def test_error_message_includes_available_pipelines(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that error includes list of available pipelines."""
        with patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock_registry,
        ):
            with pytest.raises(click.BadParameter) as exc_info:
                validate_pipeline_name(None, None, "bad_pipeline")

        assert "Available:" in str(exc_info.value)


@pytest.mark.unit
class TestGetRunnerLogger:
    """Tests for get_runner_logger helper."""

    def test_returns_logger_attribute(self) -> None:
        """Test returns 'logger' attribute from runner."""
        mock_logger = MagicMock()
        runner = MagicMock()
        runner.logger = mock_logger
        runner._logger = None

        result = get_runner_logger(runner)
        assert result is mock_logger

    def test_falls_back_to_private_logger(self) -> None:
        """Test falls back to '_logger' when 'logger' is None."""
        mock_logger = MagicMock()
        runner = MagicMock()
        runner.logger = None
        runner._logger = mock_logger

        result = get_runner_logger(runner)
        assert result is mock_logger

    def test_returns_none_when_no_logger(self) -> None:
        """Test returns None when runner has no logger attributes."""
        runner = MagicMock(spec=[])  # No attributes defined

        result = get_runner_logger(runner)
        assert result is None


@pytest.mark.unit
class TestHandleDestructiveRunConfirmation:
    """Tests for handle_destructive_run_confirmation helper."""

    def test_incremental_run_returns_true_without_prompt(self) -> None:
        """Test incremental run bypasses destructive confirmation."""
        result = handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="incremental",
            dry_run=False,
            yes=False,
        )
        assert result is True

    def test_rebuild_dry_run_returns_false(self) -> None:
        """Test rebuild + dry_run shows preview and returns False."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.show_cleanup_preview"
        ) as mock_show_cleanup_preview:
            result = handle_destructive_run_confirmation(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=True,
                yes=False,
            )

        assert result is False
        mock_show_cleanup_preview.assert_called_once_with("chembl_activity")

    def test_rebuild_with_yes_flag_returns_true(self) -> None:
        """Test rebuild with --yes bypasses interactive confirmation."""
        with patch("click.confirm", return_value=True) as mock_confirm:
            result = handle_destructive_run_confirmation(
                pipeline="chembl_activity",
                run_type="rebuild",
                dry_run=False,
                yes=True,
            )

        assert result is True
        mock_confirm.assert_not_called()


@pytest.mark.unit
class TestShowCleanupPreview:
    """Tests for show_cleanup_preview synchronous wrapper."""

    def test_show_cleanup_preview_calls_async_preview(self) -> None:
        """Test that show_cleanup_preview invokes async preview logic."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support._preview_cleanup_async",
            new_callable=AsyncMock,
        ) as mock_preview:
            show_cleanup_preview("chembl_activity")

        mock_preview.assert_awaited_once_with("chembl_activity")
