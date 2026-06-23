"""Unit tests for CsvFilterReader."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.domain.filtering import FilterLoadResult
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader


def _write_csv(tmp_path: Path, name: str, lines: list[str]) -> str:
    path = tmp_path / name
    path.write_text("".join(lines), encoding="utf-8")
    return str(path)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock LoggerPort."""
    return MagicMock()


@pytest.fixture
def csv_reader():
    """Create a CsvFilterReader instance without logger."""
    return CsvFilterReader()


@pytest.fixture
def csv_reader_with_logger(mock_logger: MagicMock) -> CsvFilterReader:
    """Create a CsvFilterReader instance with mock logger."""
    return CsvFilterReader(logger=mock_logger)


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

    async def test_load_filter_ids_returns_filter_load_result(
        self, csv_reader, sample_csv_file
    ):
        """Test that load_filter_ids returns FilterLoadResult."""
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        assert isinstance(result, FilterLoadResult)
        assert isinstance(result.ids, tuple)
        assert len(result.ids) == 3  # Duplicates removed
        assert "CHEMBL25" in result.ids
        assert "CHEMBL612545" in result.ids
        assert "CHEMBL1201198" in result.ids
        # Verify sorted order
        assert list(result.ids) == sorted(result.ids)

    async def test_load_filter_ids_reports_duplicates(
        self, csv_reader, sample_csv_file
    ):
        """Test that duplicates are detected and reported."""
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        assert result.total_count == 4  # Total rows
        assert result.unique_count == 3  # Unique IDs
        assert result.duplicate_count == 1  # One duplicate entry
        assert result.has_duplicates is True
        assert "CHEMBL25" in result.duplicates  # CHEMBL25 was duplicated

    async def test_load_filter_ids_returns_unique(self, csv_reader, sample_csv_file):
        """Test that duplicates are removed from ids."""
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        # CHEMBL25 appears twice but should only be in ids once
        assert len([x for x in result.ids if x == "CHEMBL25"]) == 1

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

        assert "VALUE3" in result.ids  # Should be trimmed

    async def test_load_filter_ids_skips_empty_values(
        self, csv_reader, csv_with_empty_values
    ):
        """Test that empty values are skipped."""
        result = await csv_reader.load_filter_ids(csv_with_empty_values, "id")

        assert "" not in result.ids
        # Only non-empty values should be present
        assert result.unique_count == 3  # VALUE1, VALUE2, VALUE3

    async def test_load_filter_ids_no_duplicates(
        self, csv_reader, csv_with_empty_values
    ):
        """Test has_duplicates is False when no duplicates."""
        result = await csv_reader.load_filter_ids(csv_with_empty_values, "id")

        assert result.has_duplicates is False
        assert result.duplicate_count == 0
        assert len(result.duplicates) == 0


@pytest.mark.unit
class TestCsvFilterReaderEdgeCases:
    """Edge case tests for CsvFilterReader."""

    async def test_load_from_empty_csv(self, csv_reader, tmp_path: Path):
        """Test loading from CSV with only headers."""
        path = _write_csv(tmp_path, "empty.csv", ["id,name\n"])

        result = await csv_reader.load_filter_ids(path, "id")
        assert result.unique_count == 0
        assert len(result.ids) == 0

    async def test_load_numeric_column_as_string(self, csv_reader, tmp_path: Path):
        """Test that numeric values are converted to strings."""
        path = _write_csv(
            tmp_path,
            "numeric.csv",
            ["id,value\n", "123,100\n", "456,200\n"],
        )

        result = await csv_reader.load_filter_ids(path, "id")
        assert "123" in result.ids
        assert "456" in result.ids
        assert all(isinstance(x, str) for x in result.ids)

    async def test_load_large_csv(self, csv_reader, tmp_path: Path):
        """Test loading from a larger CSV file."""
        path = _write_csv(
            tmp_path,
            "large.csv",
            ["id\n", *[f"ID_{i}\n" for i in range(1000)]],
        )

        result = await csv_reader.load_filter_ids(path, "id")
        assert result.unique_count == 1000

    async def test_load_with_special_characters(self, csv_reader, tmp_path: Path):
        """Test loading IDs with special characters."""
        path = _write_csv(
            tmp_path,
            "special.csv",
            [
                "id\n",
                "ID-WITH-DASH\n",
                "ID_WITH_UNDERSCORE\n",
                "ID.WITH.DOT\n",
            ],
        )

        result = await csv_reader.load_filter_ids(path, "id")
        assert "ID-WITH-DASH" in result.ids
        assert "ID_WITH_UNDERSCORE" in result.ids
        assert "ID.WITH.DOT" in result.ids

    async def test_load_malformed_csv_missing_column(self, csv_reader, tmp_path: Path):
        """Test handling of CSV where requested column is missing.

        Note: Polars is very lenient with CSV parsing and will interpret
        binary/malformed data as column names. We verify that our code
        raises a helpful error when the column isn't found.
        """
        path = _write_csv(tmp_path, "malformed.csv", ["other_column\n", "value1\n"])

        with pytest.raises(ValueError, match="Column 'id' not found"):
            await csv_reader.load_filter_ids(path, "id")

    async def test_load_with_many_duplicates(self, csv_reader, tmp_path: Path):
        """Test loading CSV with many duplicates."""
        path = _write_csv(
            tmp_path,
            "duplicates.csv",
            [
                "id\n",
                *["DUPLICATE_ID\n" for _ in range(5)],
                "UNIQUE_1\n",
                "UNIQUE_2\n",
            ],
        )

        result = await csv_reader.load_filter_ids(path, "id")
        assert result.total_count == 7
        assert result.unique_count == 3
        assert result.duplicate_count == 4  # 5 rows - 1 unique = 4 duplicates
        assert "DUPLICATE_ID" in result.duplicates


@pytest.mark.unit
class TestCsvFilterReaderLogging:
    """Tests for CsvFilterReader logging functionality."""

    async def test_logs_warning_when_duplicates_found(
        self,
        csv_reader_with_logger: CsvFilterReader,
        mock_logger: MagicMock,
        tmp_path: Path,
    ):
        """Test that warning is logged when duplicates are detected."""
        path = _write_csv(
            tmp_path,
            "logging-duplicates.csv",
            ["id\n", "DUPLICATE\n", "DUPLICATE\n", "UNIQUE\n"],
        )

        await csv_reader_with_logger.load_filter_ids(path, "id")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "filter_ids_duplicates_found"
        assert call_args[1]["duplicate_count"] == 1
        assert call_args[1]["unique_count"] == 2

    async def test_no_warning_when_no_duplicates(
        self,
        csv_reader_with_logger: CsvFilterReader,
        mock_logger: MagicMock,
        tmp_path: Path,
    ):
        """Test that no warning is logged when there are no duplicates."""
        path = _write_csv(
            tmp_path,
            "logging-clean.csv",
            ["id\n", "ID1\n", "ID2\n", "ID3\n"],
        )

        await csv_reader_with_logger.load_filter_ids(path, "id")

        mock_logger.warning.assert_not_called()

    async def test_works_without_logger(self, csv_reader, sample_csv_file):
        """Test that CsvFilterReader works correctly without a logger."""
        # Should not raise any exception
        result = await csv_reader.load_filter_ids(sample_csv_file, "molecule_id")

        assert result.has_duplicates is True
        assert result.unique_count == 3


@pytest.mark.unit
class TestCsvFilterReaderLoadFilterWithFallback:
    """Tests for CsvFilterReader.load_filter_with_fallback method."""

    @pytest.fixture
    def csv_with_fallback_data(self):
        """Create a CSV file with primary and fallback columns."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("doi,title,author\n")
            f.write("10.1000/abc123,First Paper Title,Author A\n")
            f.write("10.1000/def456,Second Paper Title,Author B\n")
            f.write("10.1000/ghi789,Third Paper Title,Author C\n")
            f.write("10.1000/abc123,Duplicate DOI Title,Author D\n")  # Duplicate
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    async def test_load_filter_with_fallback_returns_tuple(
        self, csv_reader, csv_with_fallback_data
    ):
        """Test that load_filter_with_fallback returns tuple of result and mapping."""
        result, mapping = await csv_reader.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "title"
        )

        assert isinstance(result, FilterLoadResult)
        assert isinstance(mapping, dict)

    async def test_load_filter_with_fallback_loads_primary_ids(
        self, csv_reader, csv_with_fallback_data
    ):
        """Test that load_filter_with_fallback loads primary IDs correctly."""
        result, _ = await csv_reader.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "title"
        )

        assert result.unique_count == 3
        assert "10.1000/abc123" in result.ids
        assert "10.1000/def456" in result.ids
        assert "10.1000/ghi789" in result.ids

    async def test_load_filter_with_fallback_builds_mapping(
        self, csv_reader, csv_with_fallback_data
    ):
        """Test that load_filter_with_fallback builds correct fallback mapping."""
        _, mapping = await csv_reader.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "title"
        )

        # Mapping is keyed by unique primary IDs, so 3 entries (not 4)
        assert len(mapping) == 3
        # The last value for duplicate key wins
        assert mapping["10.1000/abc123"] == "Duplicate DOI Title"
        assert mapping["10.1000/def456"] == "Second Paper Title"
        assert mapping["10.1000/ghi789"] == "Third Paper Title"

    async def test_load_filter_with_fallback_reports_duplicates(
        self, csv_reader, csv_with_fallback_data
    ):
        """Test that load_filter_with_fallback reports duplicates."""
        result, _ = await csv_reader.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "title"
        )

        assert result.has_duplicates is True
        assert result.duplicate_count == 1
        assert "10.1000/abc123" in result.duplicates

    async def test_load_filter_with_fallback_missing_fallback_column(
        self, csv_reader_with_logger, mock_logger, csv_with_fallback_data
    ):
        """Test behavior when fallback column is missing."""
        result, mapping = await csv_reader_with_logger.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "nonexistent_column"
        )

        assert result.unique_count == 3  # Primary IDs still loaded
        assert len(mapping) == 0  # Empty mapping when column missing
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "fallback_column_not_found"

    async def test_load_filter_with_fallback_logs_success(
        self, csv_reader_with_logger, mock_logger, csv_with_fallback_data
    ):
        """Test that successful loading logs info message."""
        await csv_reader_with_logger.load_filter_with_fallback(
            csv_with_fallback_data, "doi", "title"
        )

        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "fallback_mapping_loaded"
        # Mapping count is 3 (unique keys), not 4 (total rows)
        assert call_args[1]["mapping_count"] == 3

    async def test_load_filter_with_fallback_handles_empty_values(
        self, csv_reader, tmp_path: Path
    ):
        """Test that empty primary/fallback values are handled."""
        path = _write_csv(
            tmp_path,
            "fallback-empty.csv",
            [
                "doi,title\n",
                "10.1000/valid,Valid Title\n",
                ",Empty DOI Title\n",
                "10.1000/notitle,\n",
            ],
        )

        result, mapping = await csv_reader.load_filter_with_fallback(
            path, "doi", "title"
        )

        assert "" not in result.ids
        assert "__title_only_0__" in result.ids
        assert "10.1000/valid" in mapping
        assert mapping["10.1000/valid"] == "Valid Title"
        assert "__title_only_0__" in mapping
        assert mapping["__title_only_0__"] == "Empty DOI Title"
        assert "10.1000/notitle" not in mapping  # No fallback value

    async def test_load_filter_with_fallback_multiple_title_only_entries(
        self, csv_reader, tmp_path: Path
    ):
        """Test that multiple title-only entries get unique markers."""
        path = _write_csv(
            tmp_path,
            "fallback-title-only.csv",
            [
                "doi,title\n",
                "10.1000/valid,Valid Title\n",
                ",First Title Only\n",
                ",Second Title Only\n",
                ",Third Title Only\n",
            ],
        )

        result, mapping = await csv_reader.load_filter_with_fallback(
            path, "doi", "title"
        )

        assert "__title_only_0__" in result.ids
        assert "__title_only_1__" in result.ids
        assert "__title_only_2__" in result.ids
        assert mapping["__title_only_0__"] == "First Title Only"
        assert mapping["__title_only_1__"] == "Second Title Only"
        assert mapping["__title_only_2__"] == "Third Title Only"
        assert result.total_count == 4
        assert len(result.ids) == 4  # 1 DOI + 3 markers


@pytest.mark.unit
class TestCsvFilterReaderLoadMultiColumnFilter:
    """Tests for CsvFilterReader.load_multi_column_filter method."""

    @pytest.fixture
    def multi_column_csv(self):
        """Create a CSV file with multiple filter columns."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("target_id,assay_id,compound_id\n")
            f.write("T001,A001,C001\n")
            f.write("T001,A002,C002\n")
            f.write("T002,A001,C003\n")
            f.write("T002,A003,C001\n")
            path = f.name
        yield path
        Path(path).unlink(missing_ok=True)

    async def test_load_multi_column_filter_returns_filter_load_result(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter returns FilterLoadResult."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
            FilterColumn(column_name="assay_id", filter_field="assay_id"),
        ]

        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)

        assert isinstance(result, FilterLoadResult)

    async def test_load_multi_column_filter_extracts_column_ids(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter extracts unique IDs per column."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
            FilterColumn(column_name="assay_id", filter_field="assay_id"),
        ]

        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)

        assert "target_id" in result.column_ids
        assert "assay_id" in result.column_ids
        assert set(result.column_ids["target_id"]) == {"T001", "T002"}
        assert set(result.column_ids["assay_id"]) == {"A001", "A002", "A003"}

    async def test_load_multi_column_filter_builds_valid_combinations(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter builds valid row combinations."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
            FilterColumn(column_name="assay_id", filter_field="assay_id"),
        ]

        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)

        assert result.valid_combinations is not None
        assert len(result.valid_combinations) == 4
        assert ("T001", "A001") in result.valid_combinations
        assert ("T001", "A002") in result.valid_combinations
        assert ("T002", "A001") in result.valid_combinations
        assert ("T002", "A003") in result.valid_combinations
        # Invalid combination should not be present
        assert ("T001", "A003") not in result.valid_combinations

    async def test_load_multi_column_filter_sets_filter_fields(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter sets filter_fields tuple."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
            FilterColumn(column_name="assay_id", filter_field="assay_id"),
        ]

        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)

        assert result.filter_fields == ("target_id", "assay_id")

    async def test_load_multi_column_filter_sets_total_count(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter sets total_count correctly."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
        ]

        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)

        assert result.total_count == 4  # 4 rows in the CSV

    async def test_load_multi_column_filter_handles_empty_values(
        self, csv_reader, tmp_path: Path
    ):
        """Test that load_multi_column_filter handles rows with empty values."""
        from bioetl.domain.filtering import FilterColumn

        path = _write_csv(
            tmp_path,
            "multi-column-empty.csv",
            [
                "target_id,assay_id\n",
                "T001,A001\n",
                ",A002\n",
                "T002,\n",
                "T003,A003\n",
            ],
        )

        columns = [
            FilterColumn(column_name="target_id", filter_field="target"),
            FilterColumn(column_name="assay_id", filter_field="assay"),
        ]

        result = await csv_reader.load_multi_column_filter(path, columns)

        assert len(result.valid_combinations) == 2
        assert ("T001", "A001") in result.valid_combinations
        assert ("T003", "A003") in result.valid_combinations

    async def test_load_multi_column_filter_logs_info(
        self, csv_reader_with_logger, mock_logger, multi_column_csv
    ):
        """Test that load_multi_column_filter logs info message."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
            FilterColumn(column_name="assay_id", filter_field="assay_id"),
        ]

        await csv_reader_with_logger.load_multi_column_filter(multi_column_csv, columns)

        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "multi_column_filter_loaded"
        assert call_args[1]["total_rows"] == 4
        assert call_args[1]["valid_combinations"] == 4

    async def test_load_multi_column_filter_no_logger(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter works without logger."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="target_id", filter_field="target_id"),
        ]

        # Should not raise any exception
        result = await csv_reader.load_multi_column_filter(multi_column_csv, columns)
        assert result.total_count == 4

    async def test_load_multi_column_filter_column_not_found(
        self, csv_reader, multi_column_csv
    ):
        """Test that load_multi_column_filter raises for missing column."""
        from bioetl.domain.filtering import FilterColumn

        columns = [
            FilterColumn(column_name="nonexistent", filter_field="field"),
        ]

        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            await csv_reader.load_multi_column_filter(multi_column_csv, columns)
