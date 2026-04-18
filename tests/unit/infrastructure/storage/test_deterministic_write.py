"""Tests for deterministic write functionality.

Verifies that records are written in a deterministic order regardless
of input order, ensuring reproducible output files.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.export.csv_exporter import CsvExporter


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


class TestDeterministicCsvExport:
    """Tests for deterministic CSV export."""

    @pytest.fixture
    def csv_exporter(self, tmp_path: Path, mock_logger: MagicMock) -> CsvExporter:
        """Create CSV exporter with sort_by configuration."""
        return CsvExporter(
            base_path=str(tmp_path),
            logger=mock_logger,
            sort_by=["id", "name"],
            sort_ascending=True,
        )

    @pytest.fixture
    def sample_records(self) -> list[dict]:
        """Sample records in random order."""
        return [
            {"id": "C", "name": "Charlie", "value": 3},
            {"id": "A", "name": "Alice", "value": 1},
            {"id": "B", "name": "Bob", "value": 2},
        ]

    @pytest.fixture
    def sample_table(self, sample_records: list[dict]) -> pa.Table:
        """Create PyArrow table from sample records."""
        return pa.Table.from_pylist(sample_records)

    async def test_csv_export_is_sorted(
        self, csv_exporter: CsvExporter, sample_table: pa.Table, tmp_path: Path
    ):
        """Test that CSV export sorts records by specified columns."""
        csv_path = await csv_exporter.export("test_table", sample_table, append=False)

        # Read back and verify order
        lines = (
            await asyncio.to_thread(Path(csv_path).read_text, encoding="utf-8")
        ).splitlines(keepends=True)

        # Skip header
        data_lines = lines[1:]
        # Strip quotes and whitespace from id field
        ids = [line.split(",")[0].strip().replace('"', "") for line in data_lines]

        assert ids == ["A", "B", "C"], "Records should be sorted by id column"

    async def test_csv_export_deterministic_across_runs(
        self, tmp_path: Path, sample_records: list[dict], mock_logger: MagicMock
    ):
        """Test that multiple exports produce identical output."""
        outputs = []

        for i in range(3):
            # Rotate/reverse records to simulate different input orders deterministically.
            shuffled = _reorder_records(sample_records, i)

            exporter = CsvExporter(
                base_path=str(tmp_path / f"run_{i}"),
                logger=mock_logger,
                sort_by=["id"],
                sort_ascending=True,
            )

            table = pa.Table.from_pylist(shuffled)
            csv_path = await exporter.export("test", table, append=False)

            outputs.append(
                await asyncio.to_thread(Path(csv_path).read_text, encoding="utf-8")
            )

        # All outputs should be identical
        assert outputs[0] == outputs[1] == outputs[2], (
            "CSV exports should be identical regardless of input order"
        )

    async def test_csv_export_with_complex_types_sorted(
        self, csv_exporter: CsvExporter, tmp_path: Path
    ):
        """Test that complex types are serialized deterministically."""
        records = [
            {"id": "B", "name": "Bob", "tags": ["z", "a", "m"]},
            {"id": "A", "name": "Alice", "tags": ["x", "y"]},
        ]
        table = pa.Table.from_pylist(records)

        csv_path = await csv_exporter.export("complex_test", table, append=False)

        content = await asyncio.to_thread(Path(csv_path).read_text, encoding="utf-8")

        # First data row should be Alice (sorted by id)
        lines = content.strip().split("\n")
        assert "A" in lines[1], "First record should be Alice (id=A)"


def _reorder_records(records: list[dict], variant: int) -> list[dict]:
    if variant % 3 == 0:
        return list(reversed(records))
    if variant % 3 == 1:
        return records[1:] + records[:1]
    return records[2:] + records[:2]

    async def test_json_serialization_with_sort_keys(
        self, tmp_path: Path, mock_logger: MagicMock
    ):
        """Test that JSON serialization uses sort_keys=True."""
        records = [
            {"id": "A", "data": {"z_key": 1, "a_key": 2, "m_key": 3}},
        ]
        table = pa.Table.from_pylist(records)

        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=mock_logger,
            sort_by=["id"],
        )

        csv_path = await exporter.export("json_test", table, append=False)

        content = await asyncio.to_thread(Path(csv_path).read_text, encoding="utf-8")

        # JSON should have keys in alphabetical order
        assert '"a_key"' in content
        # Check that a_key comes before z_key in the serialized JSON
        a_pos = content.find('"a_key"')
        z_pos = content.find('"z_key"')
        assert a_pos < z_pos, "JSON keys should be sorted alphabetically"


class TestDeterministicBronzeWrite:
    """Tests for deterministic Bronze layer write."""

    def test_json_strings_are_sorted(self):
        """Test that Bronze JSON strings are sorted for deterministic output."""
        records = [
            {"id": "C", "value": 3},
            {"id": "A", "value": 1},
            {"id": "B", "value": 2},
        ]

        # Simulate Bronze write logic
        json_strings = [json.dumps(r, sort_keys=True) for r in records]
        json_strings.sort()

        # Verify sorted order
        parsed = [json.loads(s) for s in json_strings]
        ids = [r["id"] for r in parsed]

        assert ids == ["A", "B", "C"], "JSON strings should be sorted"

    def test_json_key_order_is_deterministic(self):
        """Test that JSON keys are always in the same order."""
        record = {"z_key": 1, "a_key": 2, "m_key": 3}

        json_str = json.dumps(record, sort_keys=True)

        # Keys should be in alphabetical order
        assert json_str == '{"a_key": 2, "m_key": 3, "z_key": 1}'


class TestDeterministicCsvFilterRead:
    """Tests for deterministic CSV filter ID reading."""

    async def test_csv_filter_reader_returns_sorted_tuple(self, tmp_path: Path):
        """Test that CsvFilterReader returns FilterLoadResult with sorted IDs."""
        from bioetl.domain.filtering import FilterLoadResult
        from bioetl.infrastructure.adapters.input.csv_filter_reader import (
            CsvFilterReader,
        )

        # Create CSV with IDs in random order
        csv_file = tmp_path / "filter_ids.csv"
        csv_file.write_text("id\nC_ID\nA_ID\nB_ID\nZ_ID\nD_ID\n")

        reader = CsvFilterReader()
        result = await reader.load_filter_ids(str(csv_file), "id")

        assert isinstance(result, FilterLoadResult), "Should return FilterLoadResult"
        assert isinstance(result.ids, tuple), "IDs should be a tuple"
        assert result.ids == (
            "A_ID",
            "B_ID",
            "C_ID",
            "D_ID",
            "Z_ID",
        ), "IDs should be sorted alphabetically"

    async def test_csv_filter_reader_deterministic_across_runs(self, tmp_path: Path):
        """Test that multiple reads produce identical results."""
        from bioetl.infrastructure.adapters.input.csv_filter_reader import (
            CsvFilterReader,
        )

        csv_file = tmp_path / "filter_ids.csv"
        csv_file.write_text("id\nID_3\nID_1\nID_2\n")

        reader = CsvFilterReader()

        results = []
        for _ in range(5):
            result = await reader.load_filter_ids(str(csv_file), "id")
            results.append(result.ids)

        # All reads should produce identical results
        assert all(r == results[0] for r in results), (
            "Multiple reads should produce identical sorted results"
        )
        assert results[0] == ("ID_1", "ID_2", "ID_3")
