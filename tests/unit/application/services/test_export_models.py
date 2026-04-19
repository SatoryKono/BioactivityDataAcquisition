"""Direct unit tests for export service models."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-export-models-"))
ACTIVITY_CSV_PATH = TEST_ROOT / "activity.csv"
SILVER_ACTIVITY_PATH = TEST_ROOT / "silver" / "activity"


@pytest.mark.unit
class TestExportResult:
    def test_success_is_true_without_error(self) -> None:
        result = ExportResult(
            table_name="silver.activity",
            layer="silver",
            format="csv",
            output_path=ACTIVITY_CSV_PATH,
            row_count=10,
        )

        assert result.success is True

    def test_success_is_false_when_error_present(self) -> None:
        result = ExportResult(
            table_name="silver.activity",
            layer="silver",
            format="xlsx",
            output_path=None,
            row_count=0,
            error="write failed",
        )

        assert result.success is False


@pytest.mark.unit
class TestExportOptionsAndTableModels:
    def test_export_options_defaults_are_stable(self) -> None:
        options = ExportOptions()

        assert options.format == "csv"
        assert options.output_path is None
        assert options.limit is None
        assert options.columns is None

    def test_preview_and_table_info_preserve_payload(self) -> None:
        preview = TablePreview(
            table_name="silver.activity",
            layer="silver",
            row_count=2,
            columns=(ColumnInfo(name="id", type="int64", nullable=False),),
            sample_rows=({"id": 1}, {"id": 2}),
        )
        table_info = TableInfo(
            name="silver.activity",
            layer="silver",
            path=SILVER_ACTIVITY_PATH,
        )

        assert preview.columns[0].name == "id"
        assert preview.sample_rows[1]["id"] == 2
        assert table_info.path == SILVER_ACTIVITY_PATH
