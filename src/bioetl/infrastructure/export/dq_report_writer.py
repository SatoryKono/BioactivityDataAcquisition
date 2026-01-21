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

    Path formats (unified structure):
    - Bronze: {base_path}/{provider}/{entity}/{date}/batch_{date}_{provider}_{entity}_dq_report{ext}
    - Silver: {base_path}/{provider}/{entity}/silver_{provider}_{entity}_dq_report{ext}
    - Gold: {base_path}/{provider}/{entity}/gold_{provider}_{entity}_dq_report{ext}
    """

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
                          with {layer}_{provider}_{entity}_dq_report{ext} naming pattern.
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
        *,
        provider: str | None = None,
        entity: str | None = None,
        date_str: str | None = None,
    ) -> Path:
        """Write Bronze DQ report to file.

        Args:
            report: Bronze DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).
            provider: Provider name for filename generation.
            entity: Entity name for filename generation.
            date_str: Date string (YYYY-MM-DD) for filename generation.

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            # Generate path based on source file location
            source_dir = Path(report.source_file).parent
            # Unified naming: batch_{date}_{provider}_{entity}_dq_report{ext}
            # Falls back to batch_id only if provider/entity not provided
            if provider and entity and date_str:
                filename = f"batch_{date_str}_{provider}_{entity}_dq_report{extension}"
            else:
                filename = f"{report.batch_id}_dq_report{extension}"
            output_path = self._base_path / source_dir / filename
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                if provider and entity and date_str:
                    filename = (
                        f"batch_{date_str}_{provider}_{entity}_dq_report{extension}"
                    )
                else:
                    filename = f"{report.batch_id}_dq_report{extension}"
                output_path = output_path / filename

        return await self._write_report(report, output_path, format)

    async def write_silver_report(
        self,
        report: SilverDQReport,
        output_path: Path | None = None,
        format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> Path:
        """Write Silver DQ report to file.

        Args:
            report: Silver DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).
            provider: Provider name for filename generation.
            entity: Entity name for filename generation.

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            # Normalize target_table: replace '.' with '/' for directory structure
            # This ensures 'chembl.activity' becomes 'chembl/activity'
            normalized_table = report.target_table.replace(".", "/")

            if self._flat_structure:
                # Flat: {base_path}/silver_{provider}_{entity}_dq_report{ext}
                if provider and entity:
                    filename = f"silver_{provider}_{entity}_dq_report{extension}"
                else:
                    flat_table_name = report.target_table.replace(".", "_")
                    filename = f"silver_{flat_table_name}_dq_report{extension}"
                output_path = self._base_path / filename
            else:
                # Unified: {base_path}/{provider}/{entity}/silver_{provider}_{entity}_dq_report{ext}
                if provider and entity:
                    filename = f"silver_{provider}_{entity}_dq_report{extension}"
                else:
                    filename = f"silver_{report.run_id}_dq_report{extension}"
                output_path = self._base_path / normalized_table / filename
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                if provider and entity:
                    filename = f"silver_{provider}_{entity}_dq_report{extension}"
                else:
                    filename = f"silver_{report.run_id}_dq_report{extension}"
                output_path = output_path / filename

        return await self._write_report(report, output_path, format)

    async def write_gold_report(
        self,
        report: GoldDQReport,
        output_path: Path | None = None,
        format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> Path:
        """Write Gold DQ report to file.

        Args:
            report: Gold DQ report to write.
            output_path: Output path (None = alongside data).
            format: Output format (None = JSON).
            provider: Provider name for filename generation.
            entity: Entity name for filename generation.

        Returns:
            Path to the written report file.
        """
        format = format or DQReportFormat.JSON
        extension = self._get_extension(format)

        if output_path is None:
            # Normalize target_table: replace '.' with '/' for directory structure
            # This ensures 'chembl.activity' becomes 'chembl/activity'
            normalized_table = report.target_table.replace(".", "/")

            if self._flat_structure:
                # Flat: {base_path}/gold_{provider}_{entity}_dq_report{ext}
                if provider and entity:
                    filename = f"gold_{provider}_{entity}_dq_report{extension}"
                else:
                    flat_table_name = report.target_table.replace(".", "_")
                    filename = f"gold_{flat_table_name}_dq_report{extension}"
                output_path = self._base_path / filename
            else:
                # Unified: {base_path}/{provider}/{entity}/gold_{provider}_{entity}_dq_report{ext}
                if provider and entity:
                    filename = f"gold_{provider}_{entity}_dq_report{extension}"
                else:
                    filename = f"gold_{report.run_id}_dq_report{extension}"
                output_path = self._base_path / normalized_table / filename
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                if provider and entity:
                    filename = f"gold_{provider}_{entity}_dq_report{extension}"
                else:
                    filename = f"gold_{report.run_id}_dq_report{extension}"
                output_path = output_path / filename

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
