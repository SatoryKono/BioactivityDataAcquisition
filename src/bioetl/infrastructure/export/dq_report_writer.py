"""DQ report writer infrastructure.

Handles writing DQ reports to the filesystem in various formats.
Implements DQReportWriterPort from domain/ports.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.services.dq_serializer import DQReportSerializer
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQReportFormat,
    GoldDQReport,
    SilverDQReport,
)
from bioetl.infrastructure.storage._atomic import atomic_write_bytes

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class DQReportWriter:
    """Writer for DQ reports to filesystem.

    Implements DQReportWriterPort with atomic writes and
    support for JSON, YAML, and HTML formats.
    """

    # Default subdirectory for DQ reports
    DQ_REPORTS_DIR = "_dq_reports"

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
    ) -> None:
        """Initialize DQ report writer.

        Args:
            base_path: Base path for report storage.
            logger: Structured logger for observability.
            flat_structure: If True, write reports directly to base_path
                          with {table_name}_dq_report{ext} naming pattern
                          instead of {table_name}/_dq_reports/{run_id}_dq_report{ext}.
        """
        self._base_path = Path(base_path)
        self._logger = logger
        self._serializer = DQReportSerializer()
        self._flat_structure = flat_structure

    async def write_bronze_report(
        self,
        report: BronzeDQReport,
        output_path: Path | None = None,
        format: DQReportFormat | None = None,
    ) -> Path:
        """Write Bronze DQ report to file.

        Args:
            report: Bronze DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            # Generate path based on source file location
            source_dir = Path(report.source_file).parent
            output_path = (
                self._base_path
                / source_dir
                / self.DQ_REPORTS_DIR
                / f"{report.batch_id}_dq_report{extension}"
            )
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / f"{report.batch_id}_dq_report{extension}"

        return await self._write_report(report, output_path, format)

    async def write_silver_report(
        self,
        report: SilverDQReport,
        output_path: Path | None = None,
        format: DQReportFormat | None = None,
    ) -> Path:
        """Write Silver DQ report to file.

        Args:
            report: Silver DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            if self._flat_structure:
                # Flat: {base_path}/{table_name}_dq_report{ext}
                output_path = (
                    self._base_path / f"{report.target_table}_dq_report{extension}"
                )
            else:
                # Nested: {base_path}/{table_name}/_dq_reports/{run_id}_dq_report{ext}
                output_path = (
                    self._base_path
                    / report.target_table
                    / self.DQ_REPORTS_DIR
                    / f"{report.run_id}_dq_report{extension}"
                )
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / f"{report.run_id}_dq_report{extension}"

        return await self._write_report(report, output_path, format)

    async def write_gold_report(
        self,
        report: GoldDQReport,
        output_path: Path | None = None,
        format: DQReportFormat | None = None,
    ) -> Path:
        """Write Gold DQ report to file.

        Args:
            report: Gold DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            if self._flat_structure:
                # Flat: {base_path}/{table_name}_dq_report{ext}
                output_path = (
                    self._base_path / f"{report.target_table}_dq_report{extension}"
                )
            else:
                # Nested: {base_path}/{table_name}/_dq_reports/{run_id}_dq_report{ext}
                output_path = (
                    self._base_path
                    / report.target_table
                    / self.DQ_REPORTS_DIR
                    / f"{report.run_id}_dq_report{extension}"
                )
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / f"{report.run_id}_dq_report{extension}"

        return await self._write_report(report, output_path, format)

    async def _write_report(
        self,
        report: BronzeDQReport | SilverDQReport | GoldDQReport,
        output_path: Path,
        format: DQReportFormat,
    ) -> Path:
        """Write report to file atomically.

        Args:
            report: DQ report to write.
            output_path: Output path for report.
            format: Output format.

        Returns:
            Path to the written report file.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize report
        content = self._serializer.serialize(report, format)
        content_bytes = content.encode("utf-8")

        # Write atomically in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: atomic_write_bytes(output_path, content_bytes),
        )

        self._logger.info(
            "dq_report_written",
            path=str(output_path),
            layer=report.layer.value,
            format=format.value,
            run_id=report.run_id,
            size_bytes=len(content_bytes),
        )

        return output_path

    def _get_extension(self, format: DQReportFormat) -> str:
        """Get file extension for format."""
        extensions = {
            DQReportFormat.JSON: ".json",
            DQReportFormat.YAML: ".yaml",
            DQReportFormat.HTML: ".html",
        }
        return extensions.get(format, ".json")


__all__ = ["DQReportWriter"]
