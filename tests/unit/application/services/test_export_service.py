"""Unit tests for ExportService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pyarrow as pa

from bioetl.application.services.export_service import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    ExportService,
    TableInfo,
    TablePreview,
)
from bioetl.domain.ports import DeltaReaderPort, LoggerPort


@pytest.fixture
def mock_reader():
    reader = AsyncMock(spec=DeltaReaderPort)
    # Use simple objects for schema fields
    class Field:
        def __init__(self, name, type, nullable):
            self.name = name
            self.type = type
            self.nullable = nullable
            
    reader.get_schema.return_value = [
        Field("col1", "string", True),
        Field("col2", "int64", False),
    ]
    reader.get_row_count.return_value = 100
    
    # Mock pyarrow table
    schema = pa.schema([("col1", pa.string()), ("col2", pa.int64())])
    data = {"col1": ["a", "b"], "col2": [1, 2]}
    table = pa.Table.from_pydict(data, schema=schema)
    reader.read_table.return_value = table
    reader.table_exists.return_value = True
    
    return reader


@pytest.fixture
def mock_logger():
    return MagicMock(spec=LoggerPort)


@pytest.fixture
def export_service(mock_reader, mock_logger, tmp_path):
    silver = tmp_path / "silver"
    gold = tmp_path / "gold"
    silver.mkdir()
    gold.mkdir()
    
    # Create dummy table structure: provider/group/table/_delta_log
    # The service expects tables to be nested under an entity/group directory
    (silver / "chembl" / "default" / "chembl.activity" / "_delta_log").mkdir(parents=True)
    
    return ExportService(
        reader=mock_reader,
        logger=mock_logger,
        silver_path=silver,
        gold_path=gold,
        export_path=tmp_path / "exports"
    )


@pytest.mark.asyncio
async def test_list_tables(export_service):
    """Test listing tables."""
    tables = export_service.list_tables(layer="all")
    assert len(tables) == 1
    assert tables[0].name == "chembl.activity"
    assert tables[0].layer == "silver"


@pytest.mark.asyncio
async def test_preview(export_service, mock_reader):
    """Test table preview."""
    preview = await export_service.preview("chembl.activity", layer="silver")
    
    assert isinstance(preview, TablePreview)
    assert preview.table_name == "chembl.activity"
    assert preview.row_count == 100
    assert len(preview.columns) == 2
    assert preview.columns[0].name == "col1"
    assert len(preview.sample_rows) == 2
    assert preview.sample_rows[0]["col1"] == "a"


@pytest.mark.asyncio
async def test_export_csv(export_service, mock_reader):
    """Test export to CSV."""
    result = await export_service.export("chembl.activity", layer="silver")
    
    assert result.success
    assert result.format == "csv"
    assert result.output_path.exists()
    assert result.output_path.name.endswith(".csv")
    assert result.row_count == 2


@pytest.mark.asyncio
async def test_export_tsv(export_service, mock_reader):
    """Test export to TSV."""
    options = ExportOptions(format="tsv")
    result = await export_service.export("chembl.activity", layer="silver", options=options)
    
    assert result.success
    assert result.format == "tsv"
    assert result.output_path.name.endswith(".tsv")


@pytest.mark.asyncio
async def test_export_table_not_found(export_service, mock_reader):
    """Test export when table not found via reader."""
    mock_reader.table_exists.return_value = False
    
    result = await export_service.export("chembl.activity", layer="silver")
    
    assert not result.success
    assert "Table not found" in result.error


@pytest.mark.asyncio
async def test_export_path_not_found(export_service):
    """Test export when table path resolution fails."""
    # Request table that doesn't exist in FS structure
    # _get_table_path raises FileNotFoundError before try/except in export
    with pytest.raises(FileNotFoundError, match="not found in silver layer"):
        await export_service.export("unknown.table", layer="silver")


@pytest.mark.asyncio
async def test_export_xlsx_import_error(export_service):
    """Test XLSX export handles missing dependency."""
    options = ExportOptions(format="xlsx")
    
    # Mock pandas to raise ImportError on to_excel with openpyxl
    # Or mock _write_xlsx_file directly if easier
    # Let's patch _write_xlsx_file inside the module
    with patch("bioetl.application.services.export_service._write_xlsx_file") as mock_write:
        mock_write.side_effect = ImportError("openpyxl missing")
        result = await export_service.export("chembl.activity", layer="silver", options=options)
        
        assert not result.success
        assert "openpyxl missing" in result.error


def test_get_table_path_invalid_layer(export_service):
    """Test _get_table_path with invalid layer."""
    with pytest.raises(ValueError):
        export_service._get_table_path("t", "bronze")


def test_get_table_path_missing_base(export_service, tmp_path):
    """Test _get_table_path when layer dir missing."""
    export_service.gold_path = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="Layer path not found"):
        export_service._get_table_path("t", "gold")
