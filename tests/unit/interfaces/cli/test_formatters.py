"""Unit tests for formatters.py.

Tests CLI output formatters.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bioetl.application.core.cleanup_service import CleanupPreview, LayerInfo
from bioetl.application.services import (
    ColumnInfo,
    ExportResult,
    TableInfo,
    TablePreview,
    TableVacuumResult,
    VacuumAllResult,
)
from bioetl.interfaces.cli.formatters import (
    echo_checkpoint,
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_export_preview,
    echo_export_result,
    echo_info,
    echo_quarantine_record,
    echo_table_list,
    echo_vacuum_all_summary,
    echo_vacuum_result,
    echo_warning,
    format_bytes,
)


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_bytes(self) -> None:
        """Test formatting bytes < 1024."""
        assert format_bytes(500) == "500 bytes"

    def test_kb(self) -> None:
        """Test formatting KB."""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1536) == "1.50 KB"

    def test_mb(self) -> None:
        """Test formatting MB."""
        assert format_bytes(1024**2) == "1.00 MB"
        assert format_bytes(1.5 * 1024**2) == "1.50 MB"

    def test_gb(self) -> None:
        """Test formatting GB."""
        assert format_bytes(1024**3) == "1.00 GB"


class TestEchoCleanupPreview:
    """Tests for echo_cleanup_preview."""

    def test_preview_exists(self, capsys: pytest.CaptureFixture) -> None:
        """Test preview when layers exist."""
        preview = CleanupPreview(
            silver=LayerInfo(path="/silver", file_count=10, exists=True),
            gold=LayerInfo(path="/gold", file_count=5, exists=True),
            total_files=15,
        )
        echo_cleanup_preview(preview)
        captured = capsys.readouterr()

        assert "Silver: /silver (10 files)" in captured.out
        assert "Gold: /gold (5 files)" in captured.out
        assert "~15" in captured.out
        assert "dry-run mode" in captured.out

    def test_preview_not_exists(self, capsys: pytest.CaptureFixture) -> None:
        """Test preview when layers do not exist."""
        preview = CleanupPreview(
            silver=LayerInfo(path="/silver", file_count=0, exists=False),
            gold=LayerInfo(path="/gold", file_count=0, exists=False),
            total_files=0,
        )
        echo_cleanup_preview(preview)
        captured = capsys.readouterr()

        assert "Silver: /silver (does not exist)" in captured.out
        assert "Gold: /gold (does not exist)" in captured.out

    def test_preview_no_gold(self, capsys: pytest.CaptureFixture) -> None:
        """Test preview when gold is None."""
        preview = CleanupPreview(
            silver=LayerInfo(path="/silver", file_count=10, exists=True),
            gold=None,
            total_files=10,
        )
        echo_cleanup_preview(preview)
        captured = capsys.readouterr()

        assert "Silver: /silver" in captured.out
        assert "Gold" not in captured.out


class TestEchoVacuumResult:
    """Tests for echo_vacuum_result."""

    def test_dry_run(self, capsys: pytest.CaptureFixture) -> None:
        """Test dry run output."""
        result = TableVacuumResult(
            table_name="table",
            layer="silver",
            files_removed=10,
        )
        echo_vacuum_result(result, dry_run=True)
        captured = capsys.readouterr()

        assert "[DRY-RUN] Would vacuum silver/table" in captured.out
        assert "Would remove 10 files" in captured.out

    def test_actual_run(self, capsys: pytest.CaptureFixture) -> None:
        """Test actual run output."""
        result = TableVacuumResult(
            table_name="table",
            layer="silver",
            files_removed=10,
        )
        echo_vacuum_result(result, dry_run=False)
        captured = capsys.readouterr()

        assert "Vacuuming silver/table" in captured.out
        assert "Removed 10 files" in captured.out

    def test_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test error output."""
        result = TableVacuumResult(
            table_name="table",
            layer="silver",
            files_removed=0,
            error="Failed",
        )
        echo_vacuum_result(result, dry_run=False)
        captured = capsys.readouterr()

        assert "Error: Failed" in captured.err


class TestEchoVacuumAllSummary:
    """Tests for echo_vacuum_all_summary."""

    def test_summary_dry_run(self, capsys: pytest.CaptureFixture) -> None:
        """Test summary for dry run."""
        table_result = TableVacuumResult(
            table_name="t1", layer="silver", files_removed=100
        )
        result = VacuumAllResult(
            results=(table_result,),
            dry_run=True,
        )
        echo_vacuum_all_summary(result)
        captured = capsys.readouterr()

        assert "Total: would remove 100 files" in captured.out

    def test_summary_actual(self, capsys: pytest.CaptureFixture) -> None:
        """Test summary for actual run."""
        t1 = TableVacuumResult(
            table_name="t1", layer="silver", files_removed=100, error="Err1"
        )
        t2 = TableVacuumResult(
            table_name="t2", layer="gold", files_removed=0, error="Err2"
        )
        result = VacuumAllResult(
            results=(t1, t2),
            dry_run=False,
        )
        echo_vacuum_all_summary(result)
        captured = capsys.readouterr()

        assert "Total: removed 100 files" in captured.out
        assert "Failed tables: silver/t1, gold/t2" in captured.err


class TestEchoQuarantineRecord:
    """Tests for echo_quarantine_record."""

    def test_record_output(self, capsys: pytest.CaptureFixture) -> None:
        """Test record output."""
        record = {"error_code": "ERR01", "payload": "data"}
        echo_quarantine_record(record)
        captured = capsys.readouterr()

        assert "Error: ERR01" in captured.out
        assert "Payload: data" in captured.out

    def test_record_missing_fields(self, capsys: pytest.CaptureFixture) -> None:
        """Test record with missing fields."""
        record = {}
        echo_quarantine_record(record)
        captured = capsys.readouterr()

        assert "Error: UNKNOWN" in captured.out
        assert "Payload: —" in captured.out


class TestEchoHelpers:
    """Tests for simple echo helpers."""

    def test_echo_checkpoint(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_checkpoint."""
        echo_checkpoint("cp1")
        captured = capsys.readouterr()
        assert "- cp1" in captured.out

    def test_echo_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_error."""
        echo_error("Main error", "Detail")
        captured = capsys.readouterr()
        assert "Main error: Detail" in captured.err

        echo_error("Just error")
        captured = capsys.readouterr()
        assert "Just error" in captured.err

    def test_echo_info(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_info."""
        echo_info("Info")
        captured = capsys.readouterr()
        assert "Info" in captured.out

    def test_echo_warning(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_warning."""
        echo_warning("Warn")
        captured = capsys.readouterr()
        assert "WARNING: Warn" in captured.out

    def test_echo_dry_run_prefix(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_dry_run_prefix."""
        echo_dry_run_prefix("Action")
        captured = capsys.readouterr()
        assert "[DRY-RUN] Action" in captured.out


class TestExportFormatters:
    """Tests for export-related formatters."""

    def test_echo_table_list(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_table_list."""
        tables = [
            TableInfo(name="t1", layer="silver", path=Path(".")),
            TableInfo(name="t2", layer="silver", path=Path(".")),
            TableInfo(name="t3", layer="gold", path=Path(".")),
        ]
        echo_table_list(tables)
        captured = capsys.readouterr()

        assert "Available Delta tables" in captured.out
        assert "SILVER:" in captured.out
        assert "GOLD:" in captured.out
        assert "t1" in captured.out
        assert "t2" in captured.out
        assert "t3" in captured.out

    def test_echo_export_preview(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_export_preview."""
        cols = [
            ColumnInfo(name="col1", type="string", nullable=True),
            ColumnInfo(name="col2", type="int", nullable=False),
        ]
        preview = TablePreview(
            table_name="t1",
            layer="silver",
            row_count=100,
            columns=tuple(cols),
            sample_rows=({"col1": "val1", "col2": 1},),
        )
        echo_export_preview(preview)
        captured = capsys.readouterr()

        assert "Table: t1 (silver)" in captured.out
        assert "Rows: 100" in captured.out
        assert "col1: string (nullable)" in captured.out
        assert "col2: int" in captured.out
        assert "val1 | 1" in captured.out

    def test_echo_export_result_success(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_export_result success."""
        result = ExportResult(
            table_name="t1",
            layer="silver",
            format="csv",
            output_path=Path("/out/file.csv"),
            row_count=100,
        )
        echo_export_result(result)
        captured = capsys.readouterr()

        assert "Exported 100 rows to CSV" in captured.out
        assert "Output: /out/file.csv" in captured.out

    def test_echo_export_result_failure(self, capsys: pytest.CaptureFixture) -> None:
        """Test echo_export_result failure."""
        result = ExportResult(
            table_name="t1",
            layer="silver",
            format="csv",
            output_path=None,
            row_count=0,
            error="Something bad",
        )
        echo_export_result(result)
        captured = capsys.readouterr()

        assert "Export failed: Something bad" in captured.err
