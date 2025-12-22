"""Unit tests for CsvExporter."""

import json
from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.export.csv_exporter import CsvExporter


@pytest.mark.unit
class TestCsvExporterInit:
    """Tests for CsvExporter initialization."""

    def test_init_with_defaults(self, tmp_path: Path) -> None:
        """Test initialization with default parameters."""
        exporter = CsvExporter(base_path=str(tmp_path))

        assert exporter.base_path == tmp_path
        assert exporter.delimiter == ","
        assert exporter.header is True
        assert exporter.encoding == "utf-8"

    def test_init_with_custom_options(self, tmp_path: Path) -> None:
        """Test initialization with custom parameters."""
        exporter = CsvExporter(
            base_path=str(tmp_path),
            delimiter=";",
            header=False,
            encoding="latin-1",
        )

        assert exporter.delimiter == ";"
        assert exporter.header is False
        assert exporter.encoding == "latin-1"


@pytest.mark.unit
class TestCsvExporterFlatten:
    """Tests for _flatten_for_csv method."""

    def test_flatten_simple_types(self) -> None:
        """Test that simple types are preserved."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
                "value": [1.5, 2.5],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert result.schema == table.schema
        assert result.to_pydict() == table.to_pydict()

    def test_flatten_list_type(self) -> None:
        """Test that list types are converted to JSON strings."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "tags": [["a", "b"], ["c"]],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert pa.types.is_string(result.schema.field("tags").type)
        assert result.column("tags").to_pylist() == ['["a", "b"]', '["c"]']

    def test_flatten_struct_type(self) -> None:
        """Test that struct types are converted to JSON strings."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "metadata": [{"key": "value1"}, {"key": "value2"}],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert pa.types.is_string(result.schema.field("metadata").type)
        metadata_list = result.column("metadata").to_pylist()
        assert json.loads(metadata_list[0]) == {"key": "value1"}
        assert json.loads(metadata_list[1]) == {"key": "value2"}

    def test_flatten_null_values(self) -> None:
        """Test that null values in complex types are handled."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "tags": [["a", "b"], None],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        tags_list = result.column("tags").to_pylist()
        assert tags_list[0] == '["a", "b"]'
        assert tags_list[1] is None


@pytest.mark.unit
class TestCsvExporterExport:
    """Tests for export method."""

    @pytest.mark.asyncio
    async def test_export_creates_file(self, tmp_path: Path) -> None:
        """Test that export creates the CSV file."""
        exporter = CsvExporter(base_path=str(tmp_path))
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
            }
        )

        result_path = await exporter.export("test_table", table)

        assert result_path.exists()
        assert result_path == tmp_path / "test_table.csv"

    @pytest.mark.asyncio
    async def test_export_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that export creates parent directories if needed."""
        nested_path = tmp_path / "nested" / "path"
        exporter = CsvExporter(base_path=str(nested_path))
        table = pa.Table.from_pydict({"id": [1]})

        result_path = await exporter.export("table", table)

        assert result_path.exists()
        assert nested_path.exists()

    @pytest.mark.asyncio
    async def test_export_with_custom_delimiter(self, tmp_path: Path) -> None:
        """Test export with custom delimiter."""
        exporter = CsvExporter(base_path=str(tmp_path), delimiter=";")
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        assert ";" in content
        # PyArrow may quote string headers
        assert '"id";"name"' in content or "id;name" in content

    @pytest.mark.asyncio
    async def test_export_without_header(self, tmp_path: Path) -> None:
        """Test export without header row."""
        exporter = CsvExporter(base_path=str(tmp_path), header=False)
        table = pa.Table.from_pydict(
            {
                "id": [1],
                "name": ["test"],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        assert "id" not in content
        assert "name" not in content
        assert "1" in content
        assert "test" in content

    @pytest.mark.asyncio
    async def test_export_complex_types(self, tmp_path: Path) -> None:
        """Test that complex types are properly serialized to JSON."""
        exporter = CsvExporter(base_path=str(tmp_path))
        table = pa.Table.from_pydict(
            {
                "id": [1],
                "tags": [["tag1", "tag2"]],
                "metadata": [{"key": "value"}],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        # CSV escapes inner quotes with double-quotes, so check for the tag content
        assert "tag1" in content and "tag2" in content
        assert "key" in content and "value" in content

    @pytest.mark.asyncio
    async def test_export_appends_to_existing_file(self, tmp_path: Path) -> None:
        """Test that export appends to existing file by default."""
        exporter = CsvExporter(base_path=str(tmp_path))

        # First export
        table1 = pa.Table.from_pydict({"id": [1], "value": ["first"]})
        await exporter.export("test", table1)

        # Second export (default: append=True)
        table2 = pa.Table.from_pydict({"id": [2], "value": ["second"]})
        result_path = await exporter.export("test", table2)

        content = result_path.read_text()
        assert "first" in content
        assert "second" in content

    @pytest.mark.asyncio
    async def test_export_overwrites_when_append_false(self, tmp_path: Path) -> None:
        """Test that export overwrites existing file when append=False."""
        exporter = CsvExporter(base_path=str(tmp_path))

        # First export
        table1 = pa.Table.from_pydict({"id": [1], "value": ["first"]})
        await exporter.export("test", table1)

        # Second export with append=False
        table2 = pa.Table.from_pydict({"id": [2], "value": ["second"]})
        result_path = await exporter.export("test", table2, append=False)

        content = result_path.read_text()
        assert "second" in content
        assert "first" not in content
