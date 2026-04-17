"""Unit tests for ExportService."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pyarrow as pa

from bioetl.application.services.export_service import (
    ExportOptions,
    ExportService,
    TablePreview,
)
from bioetl.domain.ports import (
    DeltaReaderPort,
    ExportCatalogPort,
    ExportWriterPort,
    LoggerPort,
)


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
def mock_catalog(tmp_path: Path):
    catalog = MagicMock(spec=ExportCatalogPort)
    table_path = tmp_path / "silver" / "chembl" / "default" / "chembl.activity"
    catalog.list_tables.side_effect = lambda *, base_path, layer: (
        [("chembl.activity", table_path)] if layer == "silver" else []
    )

    def _resolve_table_path(*, base_path, table_name, layer):
        del base_path
        if table_name == "chembl.activity":
            return table_path
        raise FileNotFoundError(f"Table '{table_name}' not found in {layer} layer")

    catalog.resolve_table_path.side_effect = _resolve_table_path
    return catalog


@pytest.fixture
def mock_writer():
    writer = MagicMock(spec=ExportWriterPort)

    def _write_export(
        *,
        table,
        table_name,
        layer,
        fmt,
        output_dir,
    ):
        del table
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{layer}_{table_name.replace('.', '_')}.{fmt}"
        output_path.write_text("export", encoding="utf-8")
        return output_path

    writer.write_export.side_effect = _write_export
    return writer


@pytest.fixture
def export_service(mock_reader, mock_catalog, mock_writer, mock_logger, tmp_path):
    silver = tmp_path / "silver"
    gold = tmp_path / "gold"
    silver.mkdir()
    gold.mkdir()

    (silver / "chembl" / "default" / "chembl.activity" / "_delta_log").mkdir(
        parents=True
    )

    return ExportService(
        reader=mock_reader,
        catalog=mock_catalog,
        writer=mock_writer,
        logger=mock_logger,
        silver_path=silver,
        gold_path=gold,
        export_path=tmp_path / "exports",
    )


@pytest.mark.asyncio
async def test_list_tables(export_service):
    """Test listing tables."""
    await asyncio.sleep(0)
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
    result = await export_service.export(
        "chembl.activity", layer="silver", options=options
    )

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
    export_service.writer.write_export.side_effect = ImportError("openpyxl missing")
    result = await export_service.export(
        "chembl.activity", layer="silver", options=options
    )

    assert not result.success
    assert "openpyxl missing" in result.error


def test_get_table_path_invalid_layer(export_service):
    """Test _get_table_path with invalid layer."""
    with pytest.raises(ValueError):
        export_service._get_table_path("t", "bronze")


def test_get_table_path_missing_base(export_service, tmp_path):
    """Test _get_table_path when catalog cannot resolve layer dir."""
    export_service.gold_path = tmp_path / "missing"
    export_service.catalog.resolve_table_path.side_effect = FileNotFoundError(
        f"Layer path not found: {export_service.gold_path}"
    )
    with pytest.raises(FileNotFoundError, match="Layer path not found"):
        export_service._get_table_path("t", "gold")
