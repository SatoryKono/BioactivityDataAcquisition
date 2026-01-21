"""Unit tests for export.py CLI commands.

Tests export CLI command options and service interactions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services import ExportResult, TableInfo, TablePreview
from bioetl.interfaces.cli.commands.export import export_command


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_export_service() -> MagicMock:
    """Create a mock export service."""
    service = MagicMock()
    service.list_tables = MagicMock()
    service.preview = AsyncMock()
    service.export = AsyncMock()
    return service


class TestExportCommand:
    """Tests for export command."""

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_list_tables(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test listing tables."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.list_tables.return_value = [
            TableInfo(name="chembl.activity", layer="silver", path=Path("/path/1")),
            TableInfo(name="pubchem.compound", layer="silver", path=Path("/path/2")),
        ]

        result = cli_runner.invoke(export_command, ["--list"])

        assert result.exit_code == 0
        assert "chembl.activity" in result.output
        assert "pubchem.compound" in result.output
        mock_export_service.list_tables.assert_called_once_with(layer="all")

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_list_tables_layer_silver(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test listing tables for silver layer."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.list_tables.return_value = []

        result = cli_runner.invoke(export_command, ["--list", "--layer", "silver"])

        assert result.exit_code == 0
        mock_export_service.list_tables.assert_called_once_with(layer="all")

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_list_tables_empty(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test listing tables when none found."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.list_tables.return_value = []

        result = cli_runner.invoke(export_command, ["--list"])

        assert result.exit_code == 0
        assert "No Delta tables found" in result.output

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_export_missing_table_arg(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test export without table argument."""
        mock_get_service.return_value = mock_export_service

        result = cli_runner.invoke(export_command, [])

        assert result.exit_code == 1
        assert "TABLE argument is required" in result.output

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_preview_table(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test table preview."""
        mock_get_service.return_value = mock_export_service

        # Setup mock preview
        col_mock = MagicMock()
        col_mock.name = "id"
        col_mock.type = "string"
        col_mock.nullable = False

        # Properly type columns as tuple of ColumnInfo-like objects
        # We can use the actual ColumnInfo for testing to be cleaner
        from bioetl.application.services.export_service import ColumnInfo

        cols = (ColumnInfo(name="id", type="string", nullable=False),)

        preview_data = TablePreview(
            table_name="chembl.activity",
            layer="silver",
            row_count=100,
            columns=cols,
            sample_rows=({"id": "123"},),
        )
        mock_export_service.preview.return_value = preview_data

        result = cli_runner.invoke(export_command, ["chembl.activity", "--preview"])

        assert result.exit_code == 0
        assert "Table: chembl.activity" in result.output
        assert "Rows: 100" in result.output
        assert "id: string" in result.output
        mock_export_service.preview.assert_called_once_with(
            "chembl.activity", layer="silver"
        )

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_preview_table_not_found(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test preview when table not found."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.preview.side_effect = FileNotFoundError("Table not found")

        result = cli_runner.invoke(export_command, ["missing", "--preview"])

        assert result.exit_code == 1
        assert "Table not found" in result.output

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_export_success(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test successful export."""
        mock_get_service.return_value = mock_export_service

        mock_export_service.export.return_value = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            output_path=Path("/tmp/out"),
            row_count=500,
            format="csv",
        )

        result = cli_runner.invoke(export_command, ["chembl.activity"])

        assert result.exit_code == 0
        assert "Exported 500 rows" in result.output
        assert "csv" in result.output.lower()

        # Check call args
        args, kwargs = mock_export_service.export.call_args
        assert args[0] == "chembl.activity"
        assert kwargs["layer"] == "silver"
        options = kwargs["options"]
        assert options.format == "csv"
        assert options.limit is None
        assert options.columns is None

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_export_custom_options(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test export with custom options."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.export.return_value = ExportResult(
            table_name="chembl.activity",
            layer="gold",
            output_path=Path("."),
            row_count=0,
            format="xlsx",
        )

        result = cli_runner.invoke(
            export_command,
            [
                "chembl.activity",
                "--format",
                "xlsx",
                "--layer",
                "gold",
                "--limit",
                "10",
                "--columns",
                "id,smiles",
                "--output",
                "/tmp/custom",
            ],
        )

        assert result.exit_code == 0

        # Check call args
        args, kwargs = mock_export_service.export.call_args
        assert args[0] == "chembl.activity"
        assert kwargs["layer"] == "gold"
        options = kwargs["options"]
        assert options.format == "xlsx"
        assert options.limit == 10
        assert options.columns == ["id", "smiles"]
        assert str(options.output_path) == "/tmp/custom"

    @patch("bioetl.interfaces.cli.commands.export.get_export_service")
    def test_export_failure(
        self,
        mock_get_service: MagicMock,
        mock_export_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test export failure."""
        mock_get_service.return_value = mock_export_service
        mock_export_service.export.return_value = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            output_path=None,
            row_count=0,
            format="csv",
            error="Export failed error",
        )

        result = cli_runner.invoke(export_command, ["chembl.activity"])

        assert result.exit_code == 1
        assert "Export failed: Export failed error" in result.output
