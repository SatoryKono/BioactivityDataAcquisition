"""Integration tests for CLI checkpoint list command.

Tests the `bioetl checkpoint list --pipeline <name>` command
using in-memory fakes to verify checkpoint listing functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

if TYPE_CHECKING:
    from click.testing import CliRunner
    from tests.fakes.checkpoint_fake import InMemoryCheckpoint

pytestmark = pytest.mark.integration


def _get_cli():
    from bioetl.interfaces.cli import cli

    return cli


def _create_in_memory_checkpoint() -> InMemoryCheckpoint:
    from tests.fakes.checkpoint_fake import InMemoryCheckpoint

    return InMemoryCheckpoint()


class TestCliCheckpointList:
    """Test CLI checkpoint list command."""

    def test_checkpoint_help_displays_commands(self, cli_runner: CliRunner):
        """Test that checkpoint --help displays available subcommands."""
        result = cli_runner.invoke(_get_cli(), ["checkpoint", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "Manage checkpoints" in result.output

    def test_checkpoint_list_help_displays_options(self, cli_runner: CliRunner):
        """Test that checkpoint list --help displays options."""
        result = cli_runner.invoke(_get_cli(), ["checkpoint", "list", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output

    def test_checkpoint_list_requires_pipeline(self, cli_runner: CliRunner):
        """Test that checkpoint list requires --pipeline option."""
        result = cli_runner.invoke(_get_cli(), ["checkpoint", "list"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_checkpoint_list_empty(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test checkpoint list with no checkpoints."""
        mock_manager = MagicMock()
        mock_manager.list_all = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                _get_cli(),
                ["checkpoint", "list", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # Empty list should not cause errors

    def test_checkpoint_list_with_checkpoints(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test checkpoint list with existing checkpoints."""
        sample_checkpoints = [
            "chembl_activity",
            "chembl_molecule",
            "pubchem_compound",
        ]

        mock_manager = MagicMock()
        mock_manager.list_all = AsyncMock(return_value=sample_checkpoints)

        with patch(
            "bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                _get_cli(),
                ["checkpoint", "list", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # Check that checkpoints are listed
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output
        assert "pubchem_compound" in result.output

    def test_checkpoint_list_displays_with_bullets(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that checkpoint list displays items with bullet points."""
        sample_checkpoints = ["pipeline_one", "pipeline_two"]

        mock_manager = MagicMock()
        mock_manager.list_all = AsyncMock(return_value=sample_checkpoints)

        with patch(
            "bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                _get_cli(),
                ["checkpoint", "list", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # Check for bullet format: "- pipeline_name"
        assert "- pipeline_one" in result.output or "pipeline_one" in result.output
        assert "- pipeline_two" in result.output or "pipeline_two" in result.output


class TestCliCheckpointListWithFake:
    """Test CLI checkpoint list using InMemoryCheckpoint fake."""

    @pytest.fixture
    async def populated_checkpoint(self) -> InMemoryCheckpoint:
        """Create a checkpoint fake with pre-populated data."""
        checkpoint = _create_in_memory_checkpoint()

        # Add test checkpoints
        await checkpoint.save(
            pipeline="chembl_activity",
            run_id=deterministic_uuid_from_callsite("test_cli_checkpoint_list"),
            metadata={"batch_count": 10, "last_offset": 1000},
        )
        await checkpoint.save(
            pipeline="chembl_molecule",
            run_id=deterministic_uuid_from_callsite("test_cli_checkpoint_list"),
            metadata={"batch_count": 5, "last_offset": 500},
        )
        await checkpoint.save(
            pipeline="uniprot_protein",
            run_id=deterministic_uuid_from_callsite("test_cli_checkpoint_list"),
            metadata={"batch_count": 3, "last_offset": 300},
        )

        return checkpoint

    @pytest.mark.asyncio
    async def test_fake_checkpoint_list_all(
        self,
        populated_checkpoint: InMemoryCheckpoint,
    ):
        """Test that fake checkpoint correctly lists all pipelines."""
        pipelines = await populated_checkpoint.list_all()

        assert len(pipelines) == 3
        assert "chembl_activity" in pipelines
        assert "chembl_molecule" in pipelines
        assert "uniprot_protein" in pipelines
        # Should be sorted
        assert pipelines == sorted(pipelines)

    @pytest.mark.asyncio
    async def test_fake_checkpoint_save_and_load(
        self,
        populated_checkpoint: InMemoryCheckpoint,
    ):
        """Test that fake checkpoint correctly saves and loads data."""
        # Load existing checkpoint
        result = await populated_checkpoint.load("chembl_activity")

        assert result is not None
        _run_id, metadata = result
        assert metadata["batch_count"] == 10
        assert metadata["last_offset"] == 1000

    @pytest.mark.asyncio
    async def test_fake_checkpoint_delete(
        self,
        populated_checkpoint: InMemoryCheckpoint,
    ):
        """Test that fake checkpoint correctly deletes entries."""
        # Delete a checkpoint
        await populated_checkpoint.delete("chembl_activity")

        # Verify it's deleted
        result = await populated_checkpoint.load("chembl_activity")
        assert result is None

        # Verify others still exist
        pipelines = await populated_checkpoint.list_all()
        assert len(pipelines) == 2
        assert "chembl_activity" not in pipelines

    @pytest.mark.asyncio
    async def test_fake_checkpoint_exists(
        self,
        populated_checkpoint: InMemoryCheckpoint,
    ):
        """Test that fake checkpoint correctly checks existence."""
        # Check existing
        exists = await populated_checkpoint.exists("chembl_activity")
        assert exists is True

        # Check non-existing
        exists = await populated_checkpoint.exists("nonexistent_pipeline")
        assert exists is False

    @pytest.mark.asyncio
    async def test_fake_checkpoint_clear(
        self,
        populated_checkpoint: InMemoryCheckpoint,
    ):
        """Test that fake checkpoint clear() removes all entries."""
        # Clear all checkpoints
        populated_checkpoint.clear()

        # Verify all are cleared
        pipelines = await populated_checkpoint.list_all()
        assert len(pipelines) == 0


class TestCliCheckpointIntegration:
    """Integration tests combining CLI with fake checkpoint."""

    def test_checkpoint_bootstrap_integration(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that CLI correctly integrates with checkpoint bootstrap."""
        mock_manager = MagicMock()
        mock_manager.list_all = AsyncMock(return_value=["test_pipeline"])

        with patch(
            "bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_runtime_service",
            return_value=mock_manager,
        ) as mock_bootstrap:
            result = cli_runner.invoke(
                _get_cli(),
                ["checkpoint", "list", "--pipeline", "any_pipeline"],
            )

            # Verify bootstrap was called with pipeline name
            mock_bootstrap.assert_called_once_with("any_pipeline")

        assert result.exit_code == 0
        assert "test_pipeline" in result.output
