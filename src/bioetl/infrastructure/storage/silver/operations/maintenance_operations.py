"""Maintenance operations for Silver layer (CSV export, vacuum, optimize)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import AuditPort, MetricsPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.support.retention import RetentionPolicy

if TYPE_CHECKING:
    import pyarrow as pa


class SilverMaintenanceOperations:
    """Maintenance operations for Silver layer storage.

    Handles CSV export, vacuum, optimize, and time travel operations.
    This service replaces SilverWriterMaintenanceMixin through composition.
    """

    def __init__(
        self,
        csv_exporter: CsvExporter | None,
        retention_manager: RetentionPolicy,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
    ) -> None:
        """Initialize maintenance operations.

        Args:
            csv_exporter: Optional CSV exporter for parallel output
            retention_manager: Retention policy for vacuum operations
            pipeline_name: Name of the pipeline for metric labeling
            metrics: Optional metrics port for instrumentation
            audit: Optional audit port for logging
        """
        self._csv_exporter = csv_exporter
        self._retention_manager = retention_manager
        self._pipeline_name = pipeline_name
        self._metrics = metrics
        self._audit = audit

    async def maybe_export_csv(
        self,
        table_name: str,
        arrow_data: pa.Table,
        export_path: str,
        **kwargs: Any,  # Any: Flexible CSV export options
    ) -> None:
        """Export data to CSV if exporter is configured.

        Args:
            table_name: Name of the table being exported
            arrow_data: PyArrow table to export
            export_path: Destination path for CSV file
            **kwargs: Additional export options
        """
        if self._csv_exporter is None:
            return
        _ = export_path

        if self._metrics:
            self._metrics.increment_counter(
                "bioetl_silver_csv_export_start_total",
                1,
                labels={"table": table_name, "pipeline": self._pipeline_name},
            )

        try:
            await self._csv_exporter.export(table_name, arrow_data, **kwargs)
            if self._metrics:
                self._metrics.increment_counter(
                    "bioetl_silver_csv_export_success_total",
                    1,
                    labels={"table": table_name, "pipeline": self._pipeline_name},
                )
            if self._audit:
                self._audit.log_event(
                    "SilverCsvExport",
                    {"table": table_name, "rows": len(arrow_data), "status": "success"},
                )
        except Exception as e:
            if self._metrics:
                self._metrics.increment_counter(
                    "bioetl_silver_csv_export_failures_total",
                    1,
                    labels={
                        "table": table_name,
                        "pipeline": self._pipeline_name,
                        "error_type": type(e).__name__,
                    },
                )
            if self._audit:
                self._audit.log_event(
                    "SilverCsvExport",
                    {"table": table_name, "status": "failed", "error": str(e)},
                )
            raise

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int,
        dry_run: bool = False,
    ) -> JsonDict:
        """Execute vacuum operation on Delta table.

        Args:
            table_name: Name of the table to vacuum
            retention_hours: Retention threshold in hours
            dry_run: If True, return what would be deleted without actually deleting

        Returns:
            Dictionary with vacuum operation results
        """
        if self._metrics:
            self._metrics.increment_counter("bioetl_silver_vacuum_start_total", 1)

        result = await self._retention_manager.vacuum(
            table_name, retention_hours, dry_run=dry_run
        )

        if self._metrics:
            self._metrics.increment_counter("bioetl_silver_vacuum_success_total", 1)
            self._metrics.gauge(
                "bioetl_silver_vacuum_files_removed", result.get("files_removed", 0)
            )

        if self._audit:
            self._audit.log_event(
                "SilverVacuum",
                {"table": table_name, "retention_hours": retention_hours, **result},
            )

        return result

    async def optimize(
        self,
        table_name: str,
        zorder_by: list[str] | None = None,
        **kwargs: Any,  # Any: Flexible optimize operation options
    ) -> JsonDict:
        """Execute optimize operation on Delta table.

        Args:
            table_name: Name of the table to optimize
            zorder_by: Columns to use for Z-ordering (currently unused)
            **kwargs: Additional optimize options

        Returns:
            Dictionary with optimize operation results
        """
        if self._metrics:
            self._metrics.increment_counter("bioetl_silver_optimize_start_total", 1)

        result = await self._retention_manager.optimize(
            table_name,
            target_size=kwargs.get("target_size"),
            partition_filters=kwargs.get("partition_filters"),
        )
        _ = zorder_by

        if self._metrics:
            self._metrics.increment_counter("bioetl_silver_optimize_success_total", 1)

        if self._audit:
            self._audit.log_event("SilverOptimize", result)

        return result
