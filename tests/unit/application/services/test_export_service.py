"""Unit tests for ExportService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.export_service import ExportService
from bioetl.application.services.export_models import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)


@pytest.mark.unit
class TestExportService:
    """Tests for ExportService."""

    def test_list_tables_all_layers(self):
        """Test listing tables from both silver and gold layers."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        mock_catalog.list_tables.side_effect = [
            [("activity", Path("data/silver/activity"))],
            [("compound", Path("data/gold/compound"))],
        ]

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        tables = service.list_tables(layer="all")

        assert len(tables) == 2
        assert tables[0].layer == "gold"  # Sorted by layer, name
        assert tables[0].name == "compound"
        assert tables[1].layer == "silver"
        assert tables[1].name == "activity"

    def test_list_tables_silver_only(self):
        """Test listing tables from silver layer only."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        mock_catalog.list_tables.return_value = [
            ("activity", Path("data/silver/activity"))
        ]

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        tables = service.list_tables(layer="silver")

        assert len(tables) == 1
        assert tables[0].layer == "silver"
        assert tables[0].name == "activity"
        mock_catalog.list_tables.assert_called_once()

    def test_list_tables_gold_only(self):
        """Test listing tables from gold layer only."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        mock_catalog.list_tables.return_value = [
            ("compound", Path("data/gold/compound"))
        ]

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        tables = service.list_tables(layer="gold")

        assert len(tables) == 1
        assert tables[0].layer == "gold"
        assert tables[0].name == "compound"

    async def test_preview_basic(self):
        """Test basic table preview."""
        mock_reader = AsyncMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        # Mock schema
        mock_field = MagicMock()
        mock_field.name = "id"
        mock_field.type = "int64"
        mock_field.nullable = False
        mock_reader.get_schema.return_value = [mock_field]

        # Mock row count
        mock_reader.get_row_count.return_value = 100

        # Mock sample table
        mock_table = MagicMock()
        mock_table.to_pylist.return_value = [{"id": 1}, {"id": 2}]
        mock_reader.read_table.return_value = mock_table

        mock_catalog.resolve_table_path.return_value = Path("data/silver/activity")

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        preview = await service.preview("activity", layer="silver", sample_rows=2)

        assert preview.table_name == "activity"
        assert preview.layer == "silver"
        assert preview.row_count == 100
        assert len(preview.columns) == 1
        assert preview.columns[0].name == "id"
        assert len(preview.sample_rows) == 2

    def test_get_layer_base_path_silver(self):
        """Test getting base path for silver layer."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        path = service._get_layer_base_path("silver")
        assert path == Path("data/silver")

    def test_get_layer_base_path_gold(self):
        """Test getting base path for gold layer."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        path = service._get_layer_base_path("gold")
        assert path == Path("data/gold")

    def test_get_layer_base_path_invalid(self):
        """Test that invalid layer raises ValueError."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        with pytest.raises(ValueError) as exc_info:
            service._get_layer_base_path("bronze")

        assert "Invalid layer" in str(exc_info.value)

    def test_get_table_path(self):
        """Test getting table path through catalog."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        mock_catalog.resolve_table_path.return_value = Path("data/silver/activity")

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        path = service._get_table_path("activity", "silver")

        assert path == Path("data/silver/activity")
        mock_catalog.resolve_table_path.assert_called_once_with(
            base_path=Path("data/silver"),
            table_name="activity",
            layer="silver",
        )

    def test_create_missing_table_result(self):
        """Test creating result for missing table."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        options = ExportOptions(format="csv")
        result = service._create_missing_table_result(
            table_name="activity",
            layer="silver",
            options=options,
            table_path=Path("data/silver/activity"),
        )

        assert result.table_name == "activity"
        assert result.layer == "silver"
        assert result.format == "csv"
        assert result.output_path is None
        assert result.row_count == 0
        assert result.error is not None
        assert "Table not found" in result.error

    def test_create_success_result(self):
        """Test creating result for successful export."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        options = ExportOptions(format="csv")
        manifest_paths = (Path("manifest.json"),)
        result = service._create_success_result(
            table_name="activity",
            layer="silver",
            options=options,
            output_path=Path("exports/activity.csv"),
            row_count=100,
            manifest_paths=manifest_paths,
        )

        assert result.table_name == "activity"
        assert result.layer == "silver"
        assert result.format == "csv"
        assert result.output_path == Path("exports/activity.csv")
        assert result.row_count == 100
        assert result.error is None
        assert result.manifest_paths == manifest_paths

    def test_create_failed_result(self):
        """Test creating result for failed export."""
        mock_reader = MagicMock()
        mock_catalog = MagicMock()
        mock_writer = MagicMock()
        mock_logger = MagicMock()

        service = ExportService(
            reader=mock_reader,
            catalog=mock_catalog,
            writer=mock_writer,
            logger=mock_logger,
            silver_path=Path("data/silver"),
            gold_path=Path("data/gold"),
        )

        options = ExportOptions(format="csv")
        result = service._create_failed_result(
            table_name="activity",
            layer="silver",
            options=options,
            error="Storage error",
        )

        assert result.table_name == "activity"
        assert result.layer == "silver"
        assert result.format == "csv"
        assert result.output_path is None
        assert result.row_count == 0
        assert result.error == "Storage error"
