"""Integration tests for CLI quarantine inspect command.

Tests the `bioetl quarantine inspect --pipeline <name>` command
using in-memory fakes to verify quarantine inspection functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.interfaces.cli import cli
from tests.fakes.quarantine_fake import InMemoryQuarantine

if TYPE_CHECKING:
    from click.testing import CliRunner

pytestmark = pytest.mark.integration


class TestCliQuarantineInspect:
    """Test CLI quarantine inspect command."""

    def test_quarantine_help_displays_commands(self, cli_runner: CliRunner):
        """Test that quarantine --help displays available subcommands."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])

        assert result.exit_code == 0
        assert "inspect" in result.output
        assert "Manage quarantine" in result.output or "failed records" in result.output

    def test_quarantine_inspect_help_displays_options(self, cli_runner: CliRunner):
        """Test that quarantine inspect --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--limit" in result.output
        assert "--silver-filter-only" in result.output

    def test_quarantine_inspect_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine inspect requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_quarantine_inspect_empty_quarantine(
        self,
        cli_runner: CliRunner,
        fake_quarantine: InMemoryQuarantine,
        temp_env: dict[str, str],
    ):
        """Test quarantine inspect with no records."""
        # Create mock quarantine manager that returns empty list
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "No records found" in result.output

    def test_quarantine_inspect_with_records(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test quarantine inspect with existing records."""
        # Create sample quarantine records
        sample_records = [
            {
                "error_code": "VALIDATION_ERROR",
                "payload": {"molecule_id": "CHEMBL123", "activity": "invalid"},
                "ingestion_ts": "2024-01-15T10:30:00+00:00",
            },
            {
                "error_code": "SCHEMA_MISMATCH",
                "payload": {"molecule_id": "CHEMBL456", "missing_field": None},
                "ingestion_ts": "2024-01-15T11:00:00+00:00",
            },
        ]

        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=sample_records)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # Check that records are displayed
        assert "VALIDATION_ERROR" in result.output
        assert "SCHEMA_MISMATCH" in result.output

    def test_quarantine_inspect_respects_limit(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that quarantine inspect respects --limit option."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "50",
                ],
            )

        # Verify inspect was called with correct limit (error_code=None is also passed)
        mock_manager.inspect.assert_called_once()
        inspect_kwargs = mock_manager.inspect.call_args.kwargs
        assert inspect_kwargs["limit"] == 50
        assert inspect_kwargs["error_code"] is None
        assert inspect_kwargs.get("run_id") is None
        assert result.exit_code == 0

    def test_quarantine_inspect_default_limit(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that quarantine inspect uses default limit of 100."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        # Verify inspect was called with default limit (error_code=None is also passed)
        mock_manager.inspect.assert_called_once()
        inspect_kwargs = mock_manager.inspect.call_args.kwargs
        assert inspect_kwargs["limit"] == 100
        assert inspect_kwargs["error_code"] is None
        assert inspect_kwargs.get("run_id") is None
        assert result.exit_code == 0

    def test_quarantine_inspect_displays_payload(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that quarantine inspect displays record payloads."""
        sample_records = [
            {
                "error_code": "DQ_INVALID_SMILES",
                "payload": {
                    "compound_id": "CHEMBL789",
                    "smiles": "invalid_smiles_string",
                    "activity_type": "IC50",
                },
            },
        ]

        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=sample_records)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # Check payload content is displayed
        assert "Payload:" in result.output or "payload" in result.output.lower()

    def test_quarantine_inspect_displays_structured_reason_details(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that quarantine inspect surfaces structured Silver reject reasons."""
        sample_records = [
            {
                "error_code": "FILTERED_OUT_SILVER",
                "dq_status": "NEW",
                "payload_hash": "abc123def4567890abc123def4567890",
                "payload": {"activity_id": "CHEMBL1"},
                "error_details": {
                    "message": "Missing required field",
                    "reason_code": "missing_required_field",
                    "rule_type": "required_fields",
                    "field": "publication_year",
                    "operator": "required",
                    "expected": "non-null",
                    "actual": None,
                },
            }
        ]

        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=sample_records)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                ],
            )

        assert result.exit_code == 0
        assert "Reason: Missing required field" in result.output
        assert "Reason Code: missing_required_field" in result.output
        assert "Field: publication_year" in result.output
        mock_manager.inspect.assert_called_once()
        inspect_kwargs = mock_manager.inspect.call_args.kwargs
        assert inspect_kwargs["limit"] == 100
        assert inspect_kwargs["error_code"] == "FILTERED_OUT_SILVER"
        assert inspect_kwargs.get("run_id") is None

    def test_quarantine_inspect_multiple_pipelines(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test quarantine inspect for different pipelines."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_manager,
        ) as mock_bootstrap:
            # Inspect chembl_activity
            result1 = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )
            assert result1.exit_code == 0

            # Verify correct pipeline was passed to bootstrap
            mock_bootstrap.assert_called_with("chembl_activity")


class TestCliQuarantineInspectWithFake:
    """Test CLI quarantine inspect using InMemoryQuarantine fake."""

    @pytest.fixture
    def populated_quarantine(self) -> InMemoryQuarantine:
        """Create a quarantine fake with pre-populated records."""
        quarantine = InMemoryQuarantine()

        # Add test records (synchronous method)
        quarantine.add_record(
            pipeline="chembl_activity",
            error_code="VALIDATION_ERROR",
            payload={"molecule": "CHEMBL001", "value": -1},
        )
        quarantine.add_record(
            pipeline="chembl_activity",
            error_code="VALIDATION_ERROR",
            payload={"molecule": "CHEMBL002", "value": None},
        )
        quarantine.add_record(
            pipeline="chembl_activity",
            error_code="SCHEMA_ERROR",
            payload={"molecule": "CHEMBL003", "extra_field": "unexpected"},
        )
        quarantine.add_record(
            pipeline="pubchem_compound",
            error_code="API_ERROR",
            payload={"molecule_id": "12345", "status": "failed"},
        )

        return quarantine

    @pytest.mark.asyncio
    async def test_fake_quarantine_filters_by_pipeline(
        self,
        populated_quarantine: InMemoryQuarantine,
    ):
        """Test that fake quarantine correctly filters by pipeline."""
        # Get records for chembl_activity
        chembl_records = await populated_quarantine.inspect(
            "chembl_activity", limit=100
        )
        assert len(chembl_records) == 3

        # Get records for pubchem_compound
        pubchem_records = await populated_quarantine.inspect(
            "pubchem_compound", limit=100
        )
        assert len(pubchem_records) == 1

        # Get records for non-existent pipeline
        empty_records = await populated_quarantine.inspect("nonexistent", limit=100)
        assert len(empty_records) == 0

    @pytest.mark.asyncio
    async def test_fake_quarantine_get_stats(
        self,
        populated_quarantine: InMemoryQuarantine,
    ):
        """Test that fake quarantine returns correct stats."""
        stats = await populated_quarantine.get_stats("chembl_activity")

        assert stats["total"] == 3
        assert stats["total_count"] == 3
        assert stats["by_error_code"]["VALIDATION_ERROR"] == 2
        assert stats["by_error_code"]["SCHEMA_ERROR"] == 1
