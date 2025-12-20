"""Unit tests for CsvFilterReader."""

import tempfile
from pathlib import Path

import pytest

from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader


@pytest.fixture
def csv_reader():
    """Create a CsvFilterReader instance."""
    return CsvFilterReader()


@pytest.fixture
def sample_csv_file():
    """Create a temporary CSV file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("molecule_id,name,value\n")
        f.write("CHEMBL25,Aspirin,100\n")
        f.write("CHEMBL612545,Ibuprofen,200\n")
        f.write("CHEMBL1201198,Paracetamol,150\n")
        f.write("CHEMBL25,Aspirin Duplicate,50\n")  # Duplicate ID
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def csv_with_empty_values():
    """Create a CSV file with empty and null values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("id,name\n")
        f.write("VALUE1,name1\n")
        f.write(",name2\n")  # Empty ID
        f.write("  ,name3\n")  # Whitespace only
        f.write("VALUE2,name4\n")
        f.write("  VALUE3  ,name5\n")  # Needs trimming
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.mark.unit
class TestCsvFilterReaderLoadFilterIds:
    """Tests for CsvFilterReader.load_filter_ids method."""

    async def test_load_filter_ids_basic(self, csv_reader, sample_csv_file):
        """Test basic ID loading from CSV."""
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        assert isinstance(result, set)
        assert len(result) == 3  # Duplicates removed
        assert "CHEMBL25" in result
        assert "CHEMBL612545" in result
        assert "CHEMBL1201198" in result

    async def test_load_filter_ids_returns_unique(self, csv_reader, sample_csv_file):
        """Test that duplicates are removed."""
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        # CHEMBL25 appears twice but should only be in result once
        assert len([x for x in result if x == "CHEMBL25"]) == 1

    async def test_load_filter_ids_file_not_found(self, csv_reader):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="CSV filter file not found"):
            await csv_reader.load_filter_ids("/nonexistent/path.csv", "id")

    async def test_load_filter_ids_column_not_found(self, csv_reader, sample_csv_file):
        """Test ValueError for missing column."""
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            await csv_reader.load_filter_ids(sample_csv_file, "nonexistent")

    async def test_load_filter_ids_shows_available_columns(
        self, csv_reader, sample_csv_file
    ):
        """Test that error message shows available columns."""
        with pytest.raises(ValueError, match="Available columns"):
            await csv_reader.load_filter_ids(sample_csv_file, "bad_column")

    async def test_load_filter_ids_strips_whitespace(
        self, csv_reader, csv_with_empty_values
    ):
        """Test that whitespace is stripped from values."""
        result = await csv_reader.load_filter_ids(csv_with_empty_values, "id")

        assert "VALUE3" in result  # Should be trimmed

    async def test_load_filter_ids_skips_empty_values(
        self, csv_reader, csv_with_empty_values
    ):
        """Test that empty values are skipped."""
        result = await csv_reader.load_filter_ids(csv_with_empty_values, "id")

        assert "" not in result
        # Only non-empty values should be present
        assert len(result) == 3  # VALUE1, VALUE2, VALUE3


@pytest.mark.unit
class TestCsvFilterReaderEdgeCases:
    """Edge case tests for CsvFilterReader."""

    async def test_load_from_empty_csv(self, csv_reader):
        """Test loading from CSV with only headers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,name\n")
            path = f.name

        try:
            result = await csv_reader.load_filter_ids(path, "id")
            assert len(result) == 0
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_load_numeric_column_as_string(self, csv_reader):
        """Test that numeric values are converted to strings."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id,value\n")
            f.write("123,100\n")
            f.write("456,200\n")
            path = f.name

        try:
            result = await csv_reader.load_filter_ids(path, "id")
            assert "123" in result
            assert "456" in result
            assert all(isinstance(x, str) for x in result)
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_load_large_csv(self, csv_reader):
        """Test loading from a larger CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id\n")
            for i in range(1000):
                f.write(f"ID_{i}\n")
            path = f.name

        try:
            result = await csv_reader.load_filter_ids(path, "id")
            assert len(result) == 1000
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_load_with_special_characters(self, csv_reader):
        """Test loading IDs with special characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("id\n")
            f.write("ID-WITH-DASH\n")
            f.write("ID_WITH_UNDERSCORE\n")
            f.write("ID.WITH.DOT\n")
            path = f.name

        try:
            result = await csv_reader.load_filter_ids(path, "id")
            assert "ID-WITH-DASH" in result
            assert "ID_WITH_UNDERSCORE" in result
            assert "ID.WITH.DOT" in result
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_load_invalid_csv_format(self, csv_reader):
        """Test handling of invalid CSV format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Write binary data that's not valid CSV
            f.write("\x00\x01\x02\x03")
            path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to read CSV"):
                await csv_reader.load_filter_ids(path, "id")
        finally:
            Path(path).unlink(missing_ok=True)
