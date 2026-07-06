"""Integration tests for deterministic file-backed export and filter reads."""

from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.export.csv_exporter import CsvExporter

pytestmark = pytest.mark.integration


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
        self, csv_exporter: CsvExporter, sample_table: pa.Table
    ) -> None:
        """CSV export should sort records by configured columns."""
        csv_path = await csv_exporter.export("test_table", sample_table, append=False)

        lines = Path(csv_path).read_text(encoding="utf-8").splitlines(keepends=True)
        ids = [line.split(",")[0].strip().replace('"', "") for line in lines[1:]]

        assert ids == ["A", "B", "C"]

    async def test_csv_export_deterministic_across_runs(
        self, tmp_path: Path, sample_records: list[dict], mock_logger: MagicMock
    ) -> None:
        """Repeated exports should produce byte-identical output."""
        outputs: list[str] = []

        for i in range(3):
            exporter = CsvExporter(
                base_path=str(tmp_path / f"run_{i}"),
                logger=mock_logger,
                sort_by=["id"],
                sort_ascending=True,
            )
            table = pa.Table.from_pylist(_reorder_records(sample_records, i))
            csv_path = await exporter.export("test", table, append=False)
            outputs.append(Path(csv_path).read_text(encoding="utf-8"))

        assert outputs[0] == outputs[1] == outputs[2]

    async def test_csv_export_with_complex_types_sorted(
        self, csv_exporter: CsvExporter
    ) -> None:
        """Complex types should still produce stable row order."""
        table = pa.Table.from_pylist(
            [
                {"id": "B", "name": "Bob", "tags": ["z", "a", "m"]},
                {"id": "A", "name": "Alice", "tags": ["x", "y"]},
            ]
        )

        csv_path = await csv_exporter.export("complex_test", table, append=False)
        content = Path(csv_path).read_text(encoding="utf-8")

        assert "A" in content.strip().split("\n")[1]


def _reorder_records(records: list[dict], variant: int) -> list[dict]:
    if variant % 3 == 0:
        return list(reversed(records))
    if variant % 3 == 1:
        return records[1:] + records[:1]
    return records[2:] + records[:2]


class TestDeterministicCsvFilterRead:
    """Tests for deterministic CSV filter ID reading."""

    async def test_csv_filter_reader_returns_sorted_tuple(self, tmp_path: Path) -> None:
        """CsvFilterReader should sort IDs deterministically."""
        from bioetl.domain.filtering import FilterLoadResult
        from bioetl.infrastructure.adapters.input.csv_filter_reader import (
            CsvFilterReader,
        )

        csv_file = tmp_path / "filter_ids.csv"
        csv_file.write_text("id\nC_ID\nA_ID\nB_ID\nZ_ID\nD_ID\n")

        reader = CsvFilterReader()
        result = await reader.load_filter_ids(str(csv_file), "id")

        assert isinstance(result, FilterLoadResult)
        assert isinstance(result.ids, tuple)
        assert result.ids == ("A_ID", "B_ID", "C_ID", "D_ID", "Z_ID")

    async def test_csv_filter_reader_deterministic_across_runs(
        self, tmp_path: Path
    ) -> None:
        """Repeated filter reads should produce identical sorted tuples."""
        from bioetl.infrastructure.adapters.input.csv_filter_reader import (
            CsvFilterReader,
        )

        csv_file = tmp_path / "filter_ids.csv"
        csv_file.write_text("id\nID_3\nID_1\nID_2\n")

        reader = CsvFilterReader()
        results = []
        for _ in range(5):
            results.append((await reader.load_filter_ids(str(csv_file), "id")).ids)

        assert all(result == results[0] for result in results)
        assert results[0] == ("ID_1", "ID_2", "ID_3")
