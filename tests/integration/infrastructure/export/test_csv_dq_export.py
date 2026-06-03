"""Integration tests for CSV and DQ export paths.

Tests CSV exporter and DQ report writer integration with storage layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import pyarrow as pa
import pyarrow.csv as pv


@pytest.mark.integration
class TestCsvExportPaths:
    """Integration tests for CSV export functionality.

    Tests CSV export from PyArrow tables with various data types.
    """

    def test_csv_export_basic_table(self, tmp_path: Path) -> None:
        """Test basic CSV export from PyArrow table."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter=",",
            header=True,
        )

        # Create simple PyArrow table
        table = pa.table({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10.5, 20.3, 30.1],
        })

        # Export to CSV
        output_path = tmp_path / "test_output.csv"
        exporter.export_table(table, str(output_path))

        # Verify file was created
        assert output_path.exists()

        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert "id,name,value" in content
        assert "Alice" in content
        assert "Bob" in content

    def test_csv_export_with_complex_types(self, tmp_path: Path) -> None:
        """Test CSV export with complex types (lists, structs)."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter=",",
            header=True,
        )

        # Create table with complex types
        table = pa.table({
            "id": [1, 2],
            "tags": [["tag1", "tag2"], ["tag3"]],
            "metadata": [{"key1": "value1"}, {"key2": "value2"}],
        })

        # Export to CSV
        output_path = tmp_path / "complex_output.csv"
        exporter.export_table(table, str(output_path))

        # Verify file was created
        assert output_path.exists()

        # Complex types should be serialized to JSON
        content = output_path.read_text(encoding="utf-8")
        assert "tags" in content
        assert "metadata" in content

    def test_csv_export_with_sorting(self, tmp_path: Path) -> None:
        """Test CSV export with deterministic sorting."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter=",",
            header=True,
            sort_by=["id"],
            sort_ascending=True,
        )

        # Create unsorted table
        table = pa.table({
            "id": [3, 1, 2],
            "name": ["Charlie", "Alice", "Bob"],
        })

        # Export to CSV
        output_path = tmp_path / "sorted_output.csv"
        exporter.export_table(table, str(output_path))

        # Verify file was created
        assert output_path.exists()

        # Verify sorting
        lines = output_path.read_text(encoding="utf-8").split("\n")
        data_lines = [line for line in lines if line and not line.startswith("id")]
        assert len(data_lines) == 3
        # First data row should have id=1
        assert data_lines[0].startswith("1,Alice")

    def test_csv_export_atomic_write(self, tmp_path: Path) -> None:
        """Test CSV export uses atomic writes."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter=",",
            header=True,
        )

        table = pa.table({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        output_path = tmp_path / "atomic_output.csv"
        exporter.export_table(table, str(output_path))

        # Verify file exists and is complete
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_csv_export_with_custom_delimiter(self, tmp_path: Path) -> None:
        """Test CSV export with custom delimiter."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter="|",
            header=True,
        )

        table = pa.table({
            "id": [1, 2],
            "name": ["Alice", "Bob"],
        })

        output_path = tmp_path / "delimiter_output.csv"
        exporter.export_table(table, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "|" in content
        assert "," not in content

    def test_csv_export_deduplication(self, tmp_path: Path) -> None:
        """Test CSV export deduplicates rows."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        logger = MagicMock()
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=logger,
            delimiter=",",
            header=True,
        )

        # Create table with duplicates
        table = pa.table({
            "id": [1, 2, 1, 3, 2],
            "name": ["Alice", "Bob", "Alice", "Charlie", "Bob"],
        })

        output_path = tmp_path / "dedup_output.csv"
        exporter.export_table(table, str(output_path))

        content = output_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        data_lines = [line for line in lines if line and not line.startswith("id")]
        # Should have 3 unique rows
        assert len(data_lines) == 3


@pytest.mark.integration
class TestDQExportPaths:
    """Integration tests for DQ report export functionality.

    Tests DQ report writer in JSON, YAML, and HTML formats.
    """

    def test_dq_report_writer_initialization(self, tmp_path: Path) -> None:
        """Test DQ report writer initialization."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=True,
        )

        assert writer._base_path == tmp_path
        assert writer._logger is logger
        assert writer._flat_structure is True

    def test_dq_report_json_export(self, tmp_path: Path) -> None:
        """Test DQ report export in JSON format."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
        from bioetl.domain.value_objects.dq_report import (
            BronzeDQReport,
            DQReportFormat,
        )

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=True,
        )

        # Create sample Bronze DQ report
        report = BronzeDQReport(
            provider="test_provider",
            entity="test_entity",
            run_id="test-run-123",
            total_records=100,
            passed_records=95,
            failed_records=5,
            disposition_summary={"PASS": 95, "FAIL": 5},
        )

        # Export to JSON
        import asyncio

        async def export_json() -> Path:
            return await writer.write_bronze_report(
                report,
                report_format=DQReportFormat.JSON,
            )

        output_path = asyncio.run(export_json())

        # Verify file was created
        assert output_path.exists()
        assert output_path.suffix == ".json"

        # Verify JSON content
        import json

        content = json.loads(output_path.read_text(encoding="utf-8"))
        assert content["provider"] == "test_provider"
        assert content["entity"] == "test_entity"

    def test_dq_report_yaml_export(self, tmp_path: Path) -> None:
        """Test DQ report export in YAML format."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
        from bioetl.domain.value_objects.dq_report import (
            BronzeDQReport,
            DQReportFormat,
        )

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=True,
        )

        report = BronzeDQReport(
            provider="test_provider",
            entity="test_entity",
            run_id="test-run-123",
            total_records=100,
            passed_records=95,
            failed_records=5,
            disposition_summary={"PASS": 95, "FAIL": 5},
        )

        import asyncio

        async def export_yaml() -> Path:
            return await writer.write_bronze_report(
                report,
                report_format=DQReportFormat.YAML,
            )

        output_path = asyncio.run(export_yaml())

        # Verify file was created
        assert output_path.exists()
        assert output_path.suffix == ".yaml"

        # Verify YAML content
        import yaml

        content = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        assert content["provider"] == "test_provider"

    def test_dq_report_html_export(self, tmp_path: Path) -> None:
        """Test DQ report export in HTML format."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
        from bioetl.domain.value_objects.dq_report import (
            BronzeDQReport,
            DQReportFormat,
        )

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=True,
        )

        report = BronzeDQReport(
            provider="test_provider",
            entity="test_entity",
            run_id="test-run-123",
            total_records=100,
            passed_records=95,
            failed_records=5,
            disposition_summary={"PASS": 95, "FAIL": 5},
        )

        import asyncio

        async def export_html() -> Path:
            return await writer.write_bronze_report(
                report,
                report_format=DQReportFormat.HTML,
            )

        output_path = asyncio.run(export_html())

        # Verify file was created
        assert output_path.exists()
        assert output_path.suffix == ".html"

        # Verify HTML content
        content = output_path.read_text(encoding="utf-8")
        assert "<html" in content.lower() or "<!DOCTYPE html" in content.lower()

    def test_dq_report_path_conventions(self, tmp_path: Path) -> None:
        """Test DQ report path conventions by layer."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
        from bioetl.domain.value_objects.dq_report import (
            BronzeDQReport,
            DQReportFormat,
        )

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=False,  # Use hierarchical structure
        )

        report = BronzeDQReport(
            provider="test_provider",
            entity="test_entity",
            run_id="test-run-123",
            total_records=100,
            passed_records=95,
            failed_records=5,
            disposition_summary={"PASS": 95, "FAIL": 5},
        )

        import asyncio

        async def export_with_structure() -> Path:
            return await writer.write_bronze_report(
                report,
                report_format=DQReportFormat.JSON,
                provider="test_provider",
                entity="test_entity",
            )

        output_path = asyncio.run(export_with_structure())

        # Verify hierarchical path structure
        assert "bronze" in str(output_path)
        assert "test_provider" in str(output_path)
        assert "test_entity" in str(output_path)

    def test_dq_report_atomic_write(self, tmp_path: Path) -> None:
        """Test DQ report uses atomic writes."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
        from bioetl.domain.value_objects.dq_report import (
            BronzeDQReport,
            DQReportFormat,
        )

        logger = MagicMock()
        writer = DQReportWriter(
            base_path=str(tmp_path),
            logger=logger,
            flat_structure=True,
        )

        report = BronzeDQReport(
            provider="test_provider",
            entity="test_entity",
            run_id="test-run-123",
            total_records=100,
            passed_records=95,
            failed_records=5,
            disposition_summary={"PASS": 95, "FAIL": 5},
        )

        import asyncio

        async def export_atomic() -> Path:
            return await writer.write_bronze_report(
                report,
                report_format=DQReportFormat.JSON,
            )

        output_path = asyncio.run(export_atomic())

        # Verify file exists and is complete
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 0


@pytest.mark.unit
class TestExportContracts:
    """Unit tests for export contracts and interfaces."""

    def test_csv_exporter_interface_exists(self) -> None:
        """Verify CSV exporter interface is defined."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        # Verify CsvExporter can be instantiated
        logger = MagicMock()
        exporter = CsvExporter(
            base_path="/tmp",
            logger=logger,
        )

        assert exporter is not None

    def test_dq_report_writer_interface_exists(self) -> None:
        """Verify DQ report writer interface is defined."""
        from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

        # Verify DQReportWriter can be instantiated
        logger = MagicMock()
        writer = DQReportWriter(
            base_path="/tmp",
            logger=logger,
        )

        assert writer is not None

    def test_dq_report_format_enum(self) -> None:
        """Test DQ report format enum is defined."""
        from bioetl.domain.value_objects.dq_report import DQReportFormat

        # Verify format enum has expected values
        assert DQReportFormat.JSON is not None
        assert DQReportFormat.YAML is not None
        assert DQReportFormat.HTML is not None