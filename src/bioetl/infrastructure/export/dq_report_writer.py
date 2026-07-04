"""DQ report writer infrastructure.

Handles writing DQ reports to the filesystem in various formats.
Implements DQReportWriterPort from domain/ports.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.behavior.dq_serializer import DQReportSerializer
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQReportFormat,
    GoldDQReport,
    SilverDQReport,
)
from bioetl.infrastructure.storage.atomic import atomic_write_bytes

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class DQReportWriter:
    """Writer for DQ reports to filesystem.

    Implements DQReportWriterPort with atomic writes and
    support for JSON, YAML, and HTML formats.

    Path formats (unified structure under data/output/reports/dq/):
    - Bronze: {base_path}/bronze/{provider}/{entity}/{date}/batch_{date}_{provider}_{entity}_dq_report{ext}
    - Silver: {base_path}/silver/{provider}/{entity}/silver_{provider}_{entity}_dq_report{ext}
    - Gold: {base_path}/gold/{provider}/{entity}/gold_{provider}_{entity}_dq_report{ext}

    Flat structure (when flat_structure=True):
    - Bronze: {base_path}/batch_{date}_{provider}_{entity}_dq_report{ext}
    - Silver: {base_path}/silver_{provider}_{entity}_dq_report{ext}
    - Gold: {base_path}/gold_{provider}_{entity}_dq_report{ext}
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
        report_format: DQReportFormat | None = None,
        *,
        provider: str | None = None,
        entity: str | None = None,
        date_str: str | None = None,  # Deprecated: no longer used in path/filename
    ) -> Path:
        """Write Bronze DQ report using unified Bronze/Silver/Gold path conventions.

        Returns:
            Path to the written Bronze DQ report file.
        """
        del date_str
        report_format = report_format or DQReportFormat.JSON
        extension = self._get_extension(report_format)

        # Build filename - unified with Silver pattern: {layer}_{provider}_{entity}_dq_report
        if provider and entity:
            filename = f"bronze_{provider}_{entity}_dq_report{extension}"
        else:
            filename = f"bronze_{report.batch_id}_dq_report{extension}"

        if output_path is None:
            # Unified structure: {base_path}/bronze/{provider}/{entity}/ (no date subdirectory)
            # Matches Silver/Gold pattern for consistency
            if self._flat_structure:
                output_path = self._base_path / filename
            elif provider and entity:
                output_path = self._base_path / "bronze" / provider / entity / filename
            else:
                # Fallback: extract from source file path (parent without date)
                source_dir = Path(
                    report.source_file
                ).parent.parent  # Go up from date dir
                output_path = self._base_path / source_dir / filename
        else:
            output_path = Path(output_path)
            # Treat explicit output_path as a directory and append filename.
            # Using is_dir() here is unsafe for not-yet-created directories:
            # Path(".../target").is_dir() == False before mkdir, which caused
            # reports to be written as files named "target" and later blocked
            # Bronze writer directory creation.
            output_path.mkdir(parents=True, exist_ok=True)
            output_path = output_path / filename

        return await self._write_report(report, output_path, report_format)

    def _build_layer_filename(
        self,
        layer: str,
        extension: str,
        provider: str | None,
        entity: str | None,
        target_table: str,
    ) -> str:
        """Build filename for Silver/Gold DQ report.

        Args:
            layer: Layer name ('silver' or 'gold').
            extension: File extension including dot.
            provider: Provider name for filename.
            entity: Entity name for filename.
            target_table: Target table name (fallback for naming).

        Returns:
            Generated filename.
        """
        if provider and entity:
            return f"{layer}_{provider}_{entity}_dq_report{extension}"
        normalized_table_name = target_table.replace(".", "_")
        return f"{layer}_{normalized_table_name}_dq_report{extension}"

    def _resolve_layer_output_path(
        self,
        layer: str,
        output_path: Path | None,
        extension: str,
        provider: str | None,
        entity: str | None,
        target_table: str,
    ) -> Path:
        """Resolve final report file path for Silver/Gold DQ outputs.

        Returns:
            Resolved Path for the DQ report file following the layer directory convention.
        """
        filename = self._build_layer_filename(
            layer, extension, provider, entity, target_table
        )

        if output_path is not None:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
            return output_path / filename

        if self._flat_structure:
            return self._base_path / filename

        if provider and entity:
            return self._base_path / layer / provider / entity / filename

        if "_" in target_table:
            parts = target_table.split("_", 1)
            return self._base_path / layer / parts[0] / parts[1] / filename

        return self._base_path / layer / target_table / filename

    async def write_silver_report(
        self,
        report: SilverDQReport,
        output_path: Path | None = None,
        report_format: DQReportFormat | None = None,
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
        report_format = report_format or DQReportFormat.JSON
        extension = self._get_extension(report_format)
        resolved_path = self._resolve_layer_output_path(
            "silver",
            output_path,
            extension,
            provider,
            entity,
            report.target_table,
        )
        return await self._write_report(report, resolved_path, report_format)

    async def write_gold_report(
        self,
        report: GoldDQReport,
        output_path: Path | None = None,
        report_format: DQReportFormat | None = None,
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
        report_format = report_format or DQReportFormat.JSON
        extension = self._get_extension(report_format)
        resolved_path = self._resolve_layer_output_path(
            "gold",
            output_path,
            extension,
            provider,
            entity,
            report.target_table,
        )
        return await self._write_report(report, resolved_path, report_format)

    async def _write_report(
        self,
        report: BronzeDQReport | SilverDQReport | GoldDQReport,
        output_path: Path,
        report_format: DQReportFormat,
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
        content = self._serializer.serialize(report, report_format)
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
            format=report_format.value,
            run_id=report.run_id,
            size_bytes=len(content_bytes),
        )

        return output_path

    def _get_extension(self, report_format: DQReportFormat) -> str:
        """Get file extension for report format.

        Returns:
            File extension string (e.g., '.json', '.yaml', '.html') for the given format.
        """
        extensions = {
            DQReportFormat.JSON: ".json",
            DQReportFormat.YAML: ".yaml",
            DQReportFormat.HTML: ".html",
        }
        return extensions.get(report_format, ".json")


__all__ = ["DQReportWriter"]
