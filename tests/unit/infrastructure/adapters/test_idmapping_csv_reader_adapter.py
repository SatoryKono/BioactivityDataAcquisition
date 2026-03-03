"""Unit tests for IDMappingCsvReaderAdapter."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.input.idmapping_csv_reader_adapter import (
    IDMappingCsvReaderAdapter,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock LoggerPort."""
    return MagicMock()


@pytest.fixture
def csv_reader(mock_logger: MagicMock) -> IDMappingCsvReaderAdapter:
    """Create ID mapping CSV reader adapter."""
    return IDMappingCsvReaderAdapter(logger=mock_logger)


@pytest.mark.unit
class TestIDMappingCsvReaderAdapter:
    """Tests for source reader adapter behavior."""

    async def test_read_ids_success(
        self, csv_reader: IDMappingCsvReaderAdapter
    ) -> None:
        """Test successful ID loading from CSV."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write("target_id,name\n")
            file.write("CHEMBL204,Target 1\n")
            file.write(",Empty\n")
            file.write("CHEMBL205,Target 2\n")
            path = file.name

        try:
            ids = await csv_reader.read_ids(path, "target_id")
            assert ids == ["CHEMBL204", "CHEMBL205"]
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_read_ids_file_not_found(
        self, csv_reader: IDMappingCsvReaderAdapter
    ) -> None:
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            await csv_reader.read_ids("/missing/input.csv", "target_id")

    async def test_read_ids_missing_column(
        self, csv_reader: IDMappingCsvReaderAdapter
    ) -> None:
        """Test ValueError when configured column does not exist."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write("other_column,name\n")
            file.write("VALUE,Name\n")
            path = file.name

        try:
            with pytest.raises(ValueError, match="Missing required column"):
                await csv_reader.read_ids(path, "target_id")
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_source_exists(self, csv_reader: IDMappingCsvReaderAdapter) -> None:
        """Test source existence checks."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as file:
            file.write("target_id\nCHEMBL1\n")
            path = file.name

        try:
            assert await csv_reader.source_exists(path) is True
            assert await csv_reader.source_exists(f"{path}.missing") is False
        finally:
            Path(path).unlink(missing_ok=True)
