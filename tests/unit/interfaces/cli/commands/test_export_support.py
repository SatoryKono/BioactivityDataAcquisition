"""Unit tests for export_support.py CLI helpers.

Tests export support functions including option parsing, table listing,
preview, and export execution helpers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.services import (
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.export_support import (
    _build_export_options,
    _list_tables_or_exit,
    _require_table_argument,
    _run_export,
    _run_preview,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-export-support-"))
DELTA_TABLE_PATH = TEST_ROOT / "delta" / "silver" / "chembl_activity"
EXPORT_OUTPUT_PATH = TEST_ROOT / "output.csv"


def _make_service(
    *,
    preview_result: TablePreview | None = None,
    export_result: ExportResult | None = None,
    tables: list[TableInfo] | None = None,
) -> MagicMock:
    """Create a mock _ExportCommandService."""
    service = MagicMock()
    service.preview = AsyncMock(return_value=preview_result)
    service.export = AsyncMock(return_value=export_result)
    service.list_tables = MagicMock(return_value=tables or [])
    return service


def _make_table_info(name: str = "chembl_activity") -> TableInfo:
    """Create a minimal TableInfo instance."""
    return TableInfo(
        name=name,
        layer="silver",
        path=DELTA_TABLE_PATH,
    )


def _make_table_preview() -> TablePreview:
    """Create a minimal TablePreview instance."""
    return TablePreview(
        table_name="chembl_activity",
        layer="silver",
        row_count=5,
        columns=(),
        sample_rows=(),
    )


def _make_export_result(*, error: str | None = None) -> ExportResult:
    """Create an ExportResult; error=None means success."""
    return ExportResult(
        table_name="chembl_activity",
        layer="silver",
        format="csv",
        output_path=EXPORT_OUTPUT_PATH if error is None else None,
        row_count=100 if error is None else 0,
        error=error,
    )


@pytest.mark.unit
class TestRequireTableArgument:
    """Tests for _require_table_argument helper."""

    def test_returns_table_when_provided(self) -> None:
        """Test that a non-empty table string is returned."""
        result = _require_table_argument("chembl_activity")
        assert result == "chembl_activity"

    def test_raises_system_exit_when_none(self) -> None:
        """Test that None table causes SystemExit with FAIL code."""
        with pytest.raises(SystemExit) as exc_info:
            _require_table_argument(None)

        assert exc_info.value.code == ExitCode.FAIL

    def test_raises_system_exit_when_empty_string(self) -> None:
        """Test that empty string table causes SystemExit with FAIL code."""
        with pytest.raises(SystemExit) as exc_info:
            _require_table_argument("")

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestBuildExportOptions:
    """Tests for _build_export_options helper."""

    def test_builds_csv_options(self) -> None:
        """Test that CSV format is parsed into ExportOptions."""
        options = _build_export_options(
            output_format="csv",
            output=None,
            limit=None,
            columns=None,
        )

        assert options.format == "csv"
        assert options.output_path is None
        assert options.limit is None
        assert options.columns is None

    def test_builds_options_with_output_path(self) -> None:
        """Test that output path is passed through to ExportOptions."""
        path = EXPORT_OUTPUT_PATH
        options = _build_export_options(
            output_format="csv",
            output=path,
            limit=100,
            columns=None,
        )

        assert options.output_path == path
        assert options.limit == 100

    def test_parses_columns_list(self) -> None:
        """Test that comma-separated columns string is parsed."""
        options = _build_export_options(
            output_format="csv",
            output=None,
            limit=None,
            columns="col1, col2, col3",
        )

        assert options.columns == ["col1", "col2", "col3"]

    def test_unknown_format_defaults_to_csv(self) -> None:
        """Test that unknown format falls back to csv."""
        options = _build_export_options(
            output_format="unknown_format",
            output=None,
            limit=None,
            columns=None,
        )

        assert options.format == "csv"

    def test_xlsx_format(self) -> None:
        """Test that xlsx format is accepted."""
        options = _build_export_options(
            output_format="xlsx",
            output=None,
            limit=None,
            columns=None,
        )

        assert options.format == "xlsx"


@pytest.mark.unit
class TestListTablesOrExit:
    """Tests for _list_tables_or_exit helper."""

    def test_empty_table_list_returns_without_error(self) -> None:
        """Test that empty table list exits normally after printing info."""
        service = _make_service(tables=[])

        _list_tables_or_exit(service, layer="silver")
        service.list_tables.assert_called_once()

    def test_non_empty_table_list_prints_tables(self) -> None:
        """Test that non-empty table list is printed without error."""
        table = _make_table_info()
        service = _make_service(tables=[table])

        _list_tables_or_exit(service, layer="silver")
        service.list_tables.assert_called_once()

    def test_handles_domain_error_exits_with_fail(self) -> None:
        """Test that BioETLError during listing exits with FAIL code."""
        service = MagicMock()
        service.list_tables = MagicMock(side_effect=BioETLError("list error"))

        with pytest.raises(SystemExit) as exc_info:
            _list_tables_or_exit(service, layer="silver")

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestRunPreview:
    """Tests for _run_preview helper."""

    def test_success_calls_preview_and_echoes(self) -> None:
        """Test that successful preview calls echo_export_preview."""
        preview = _make_table_preview()
        service = _make_service(preview_result=preview)

        with patch(
            "bioetl.interfaces.cli.commands.export_support.echo_export_preview"
        ) as mock_echo:
            _run_preview(service, "chembl_activity", "silver")

        mock_echo.assert_called_once_with(preview)

    def test_file_not_found_raises_system_exit(self) -> None:
        """Test that FileNotFoundError during preview raises SystemExit."""
        service = MagicMock()
        service.preview = AsyncMock(side_effect=FileNotFoundError("no table"))

        with pytest.raises(SystemExit) as exc_info:
            _run_preview(service, "nonexistent_table", "silver")

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestRunExport:
    """Tests for _run_export helper."""

    def test_success_echoes_export_result(self) -> None:
        """Test that successful export calls echo_export_result."""
        export_result = _make_export_result()
        service = _make_service(export_result=export_result)
        options = ExportOptions()

        with patch(
            "bioetl.interfaces.cli.commands.export_support.echo_export_result"
        ) as mock_echo:
            _run_export(service, "chembl_activity", "silver", options)

        mock_echo.assert_called_once_with(export_result)

    def test_failed_export_raises_system_exit(self) -> None:
        """Test that export result with error raises SystemExit."""
        export_result = _make_export_result(error="write failed")
        service = _make_service(export_result=export_result)
        options = ExportOptions()

        with patch("bioetl.interfaces.cli.commands.export_support.echo_export_result"):
            with pytest.raises(SystemExit) as exc_info:
                _run_export(service, "chembl_activity", "silver", options)

        assert exc_info.value.code == ExitCode.FAIL

    def test_domain_error_exits_with_fail(self) -> None:
        """Test that BioETLError during export exits with FAIL code."""
        service = MagicMock()
        service.export = AsyncMock(side_effect=BioETLError("export error"))
        options = ExportOptions()

        with pytest.raises(SystemExit) as exc_info:
            _run_export(service, "chembl_activity", "silver", options)

        assert exc_info.value.code == ExitCode.FAIL
