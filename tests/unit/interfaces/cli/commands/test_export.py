# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for export.py CLI command.

Tests the export command for Delta Lake table export functionality.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.interfaces.cli import cli

pytestmark = pytest.mark.unit


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_export_service() -> MagicMock:
    """Create a mock ExportService."""
    service = MagicMock()
    service.list_tables = MagicMock(return_value=[])
    service.preview = AsyncMock()
    service.export = AsyncMock()
    return service


class TestExportHelp:
    """Test export command help."""

    def test_export_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that export --help displays available options."""
        result = cli_runner.invoke(cli, ["export", "--help"])

        assert result.exit_code == 0
        assert "--list" in result.output
        assert "--preview" in result.output
        assert "--format" in result.output
        assert "--layer" in result.output
        assert "--output" in result.output
        assert "--limit" in result.output
        assert "--columns" in result.output

    def test_export_help_shows_format_choices(self, cli_runner: CliRunner) -> None:
        """Test that export --help shows format choices."""
        result = cli_runner.invoke(cli, ["export", "--help"])

        assert "csv" in result.output
        assert "xlsx" in result.output
        assert "tsv" in result.output

    def test_export_help_shows_layer_choices(self, cli_runner: CliRunner) -> None:
        """Test that export --help shows layer choices."""
        result = cli_runner.invoke(cli, ["export", "--help"])

        assert "silver" in result.output
        assert "gold" in result.output


class TestExportListTables:
    """Test export --list functionality."""

    def test_list_empty_tables(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --list with no tables found."""
        mock_export_service.list_tables.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "--list"])

        assert result.exit_code == 0
        assert "No Delta tables found" in result.output

    def test_list_tables_found(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --list with tables found."""
        mock_export_service.list_tables.return_value = [
            TableInfo(
                name="chembl_activity",
                layer="silver",
                path=Path("/data/silver/chembl/activity"),
            ),
            TableInfo(
                name="pubchem_compound",
                layer="silver",
                path=Path("/data/silver/pubchem/compound"),
            ),
            TableInfo(
                name="chembl_activity",
                layer="gold",
                path=Path("/data/gold/chembl/activity"),
            ),
        ]

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "--list"])

        assert result.exit_code == 0
        assert "Available Delta tables" in result.output
        assert "chembl_activity" in result.output
        assert "pubchem_compound" in result.output

    def test_list_tables_with_layer_filter(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --list with --layer filter."""
        mock_export_service.list_tables.return_value = [
            TableInfo(
                name="chembl_activity",
                layer="gold",
                path=Path("/data/gold/chembl/activity"),
            ),
        ]

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "--list", "--layer", "gold"])

        # When layer is "gold", it's passed directly (not "all")
        mock_export_service.list_tables.assert_called_once_with(layer="gold")
        assert result.exit_code == 0


class TestExportPreview:
    """Test export --preview functionality."""

    def test_preview_success(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --preview shows table schema and sample data."""
        preview_data = TablePreview(
            table_name="chembl.activity",
            layer="silver",
            row_count=1000,
            columns=(
                ColumnInfo(name="id", type="string", nullable=False),
                ColumnInfo(name="value", type="float64", nullable=True),
            ),
            sample_rows=(
                {"id": "1", "value": 10.5},
                {"id": "2", "value": 20.3},
            ),
        )
        mock_export_service.preview = AsyncMock(return_value=preview_data)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity", "--preview"])

        assert result.exit_code == 0
        assert "chembl.activity" in result.output
        assert "1,000" in result.output  # Row count formatted
        assert "id" in result.output
        assert "value" in result.output

    def test_preview_table_not_found(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --preview with nonexistent table."""
        mock_export_service.preview = AsyncMock(
            side_effect=FileNotFoundError("Table not found: chembl.activity")
        )

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity", "--preview"])

        assert result.exit_code == 1
        assert "Table not found" in result.output

    def test_preview_with_gold_layer(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test --preview with --layer gold."""
        preview_data = TablePreview(
            table_name="chembl.activity",
            layer="gold",
            row_count=500,
            columns=(ColumnInfo(name="id", type="string", nullable=False),),
            sample_rows=(),
        )
        mock_export_service.preview = AsyncMock(return_value=preview_data)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--preview", "--layer", "gold"]
            )

        assert result.exit_code == 0
        mock_export_service.preview.assert_called_once_with(
            "chembl.activity", layer="gold"
        )


class TestExportMissingTable:
    """Test export with missing table argument."""

    def test_export_without_table_shows_error(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test export without TABLE argument shows error."""
        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export"])

        assert result.exit_code == 1
        assert "TABLE argument is required" in result.output


class TestExportToFile:
    """Test export to file functionality."""

    def test_export_csv_success(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export to CSV format."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "silver_chembl_activity.csv",
            row_count=100,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity"])

        assert result.exit_code == 0
        assert "100" in result.output  # Row count
        assert "CSV" in result.output

    def test_export_xlsx_success(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export to XLSX format."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="xlsx",
            output_path=tmp_path / "silver_chembl_activity.xlsx",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--format", "xlsx"]
            )

        assert result.exit_code == 0
        assert "50" in result.output
        assert "XLSX" in result.output

    def test_export_tsv_success(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export to TSV format."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="tsv",
            output_path=tmp_path / "silver_chembl_activity.tsv",
            row_count=75,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--format", "tsv"]
            )

        assert result.exit_code == 0
        assert "75" in result.output
        assert "TSV" in result.output

    def test_export_with_limit(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export with --limit option."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "silver_chembl_activity.csv",
            row_count=100,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--limit", "100"]
            )

        assert result.exit_code == 0
        # Verify export was called with correct options
        call_args = mock_export_service.export.call_args
        options = call_args[1]["options"]
        assert options.limit == 100

    def test_export_with_columns(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export with --columns option."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "silver_chembl_activity.csv",
            row_count=100,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--columns", "id,name,value"]
            )

        assert result.exit_code == 0
        # Verify export was called with correct columns
        call_args = mock_export_service.export.call_args
        options = call_args[1]["options"]
        assert options.columns == ["id", "name", "value"]

    def test_export_with_output_path(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export with --output option."""
        output_dir = tmp_path / "custom_output"
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=output_dir / "silver_chembl_activity.csv",
            row_count=100,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--output", str(output_dir)]
            )

        assert result.exit_code == 0
        # Verify export was called with correct output path
        call_args = mock_export_service.export.call_args
        options = call_args[1]["options"]
        assert options.output_path == output_dir

    def test_export_with_governance_options(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test governed export CLI options are propagated to the service."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "silver_chembl_activity.csv",
            row_count=100,
            audit_ref="export-audit:abc123",
            expires_at="2026-07-01T00:00:00Z",
            redaction_profile="none",
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "export",
                    "chembl.activity",
                    "--requester",
                    "operator@example.test",
                    "--role",
                    "exporter",
                    "--filters-hash",
                    "filters-sha256",
                    "--expires-at",
                    "2026-07-01T00:00:00Z",
                    "--redaction-profile",
                    "none",
                ],
            )

        assert result.exit_code == 0
        assert "Audit ref: export-audit:abc123" in result.output
        call_args = mock_export_service.export.call_args
        options = call_args[1]["options"]
        assert options.requester == "operator@example.test"
        assert options.role == "exporter"
        assert options.filters_hash == "filters-sha256"
        assert options.expires_at == "2026-07-01T00:00:00Z"
        assert options.redaction_profile == "none"

    def test_export_gold_layer(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export from gold layer."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="gold",
            format="csv",
            output_path=tmp_path / "gold_chembl_activity.csv",
            row_count=100,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "--layer", "gold"]
            )

        assert result.exit_code == 0
        # Verify export was called with gold layer
        call_args = mock_export_service.export.call_args
        assert call_args[1]["layer"] == "gold"


class TestExportFailure:
    """Test export failure scenarios."""

    def test_export_export_failure__table_not_found__f2287d08(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test export when table not found."""
        export_result = ExportResult(
            table_name="nonexistent.table",
            layer="silver",
            format="csv",
            output_path=None,
            row_count=0,
            error="Table not found: nonexistent.table",
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "nonexistent.table"])

        assert result.exit_code == 1
        assert "Export failed" in result.output
        assert "Table not found" in result.output

    def test_export_write_error(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
    ) -> None:
        """Test export when write fails."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="xlsx",
            output_path=None,
            row_count=0,
            error="openpyxl is required for XLSX export",
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity", "-f", "xlsx"])

        assert result.exit_code == 1
        assert "Export failed" in result.output


class TestExportShortOptions:
    """Test export with short option forms."""

    def test_short_format_option(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test -f short form for --format."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="tsv",
            output_path=tmp_path / "output.tsv",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity", "-f", "tsv"])

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[1]["options"].format == "tsv"

    def test_short_layer_option(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test -l short form for --layer."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="gold",
            format="csv",
            output_path=tmp_path / "output.csv",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(cli, ["export", "chembl.activity", "-l", "gold"])

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[1]["layer"] == "gold"

    def test_short_output_option(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test -o short form for --output."""
        output_dir = tmp_path / "exports"
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=output_dir / "output.csv",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "-o", str(output_dir)]
            )

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[1]["options"].output_path == output_dir

    def test_short_columns_option(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test -c short form for --columns."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "output.csv",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "-c", "id,name"]
            )

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[1]["options"].columns == ["id", "name"]


class TestExportColumnsWithSpaces:
    """Test export with column names containing spaces."""

    def test_columns_with_spaces_trimmed(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test column names with spaces are trimmed."""
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="silver",
            format="csv",
            output_path=tmp_path / "output.csv",
            row_count=50,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli, ["export", "chembl.activity", "-c", "id, name , value"]
            )

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[1]["options"].columns == ["id", "name", "value"]


class TestExportCombinedOptions:
    """Test export with multiple options combined."""

    def test_all_options_combined(
        self,
        cli_runner: CliRunner,
        mock_export_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test export with all options combined."""
        output_dir = tmp_path / "output"
        export_result = ExportResult(
            table_name="chembl.activity",
            layer="gold",
            format="xlsx",
            output_path=output_dir / "gold_chembl_activity.xlsx",
            row_count=1000,
        )
        mock_export_service.export = AsyncMock(return_value=export_result)

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=mock_export_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "export",
                    "chembl.activity",
                    "--format",
                    "xlsx",
                    "--layer",
                    "gold",
                    "--output",
                    str(output_dir),
                    "--limit",
                    "1000",
                    "--columns",
                    "id,name,value",
                ],
            )

        assert result.exit_code == 0
        call_args = mock_export_service.export.call_args
        assert call_args[0][0] == "chembl.activity"
        assert call_args[1]["layer"] == "gold"
        options = call_args[1]["options"]
        assert options.format == "xlsx"
        assert options.output_path == output_dir
        assert options.limit == 1000
        assert options.columns == ["id", "name", "value"]
