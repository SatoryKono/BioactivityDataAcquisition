"""Vacuum service for batch Delta table maintenance.

Provides high-level vacuum operations across multiple tables.
This service belongs to Application layer and orchestrates vacuum
operations without CLI-specific formatting concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class TableVacuumResult:
    """Result of vacuum operation on a single table.

    Attributes:
        table_name: Name of the vacuumed table.
        layer: Medallion layer (silver/gold).
        files_removed: Number of files removed.
        error: Error message if vacuum failed, None otherwise.
    """

    table_name: str
    layer: str
    files_removed: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if vacuum succeeded."""
        return self.error is None


@dataclass(frozen=True, slots=True)
class VacuumAllResult:
    """Result of vacuum-all operation across multiple tables.

    Attributes:
        results: List of per-table results.
        total_files_removed: Sum of files removed across all tables.
        failed_tables: List of table names that failed.
        dry_run: Whether this was a dry run.
    """

    results: tuple[TableVacuumResult, ...]
    dry_run: bool

    @property
    def total_files_removed(self) -> int:
        """Get total files removed across all tables."""
        return sum(r.files_removed for r in self.results)

    @property
    def failed_tables(self) -> list[str]:
        """Get list of failed table identifiers."""
        return [f"{r.layer}/{r.table_name}" for r in self.results if r.error]

    @property
    def success_count(self) -> int:
        """Count of successfully vacuumed tables."""
        return sum(1 for r in self.results if r.success)


@dataclass
class VacuumService:
    """Service for batch vacuum operations on Delta tables.

    Responsibilities:
    - Collect tables from pipeline registry for vacuum-all
    - Orchestrate vacuum operations across multiple tables
    - Track and report results

    This service encapsulates business logic that was previously
    in CLI (_collect_vacuum_tables, _vacuum_table).

    Attributes:
        lifecycle: MedallionLifecycleService for individual vacuum ops.
        logger: Structured logger for observability.

    Example:
        >>> service = VacuumService(lifecycle=lifecycle, logger=logger)
        >>> tables = service.collect_tables(layer="all")
        >>> result = await service.vacuum_all(tables, retention_days=7)
        >>> print(f"Removed {result.total_files_removed} files")
    """

    lifecycle: MedallionLifecycleService
    logger: LoggerPort
    _registry_factory: object = field(default=None, repr=False)

    def collect_tables(self, layer: str = "all") -> list[tuple[str, str]]:
        """Collect tables from all registered pipelines.

        Queries the pipeline registry and extracts silver/gold table names
        from each pipeline's configuration.

        Args:
            layer: Which layer to collect - "all", "silver", or "gold".

        Returns:
            List of (table_name, layer) tuples sorted alphabetically.
        """
        from bioetl.composition.entrypoints import load_pipeline_config
        from bioetl.composition.registry import get_default_registry

        registry = get_default_registry()
        pipelines = registry.list_pipelines()

        silver_tables: set[str] = set()
        gold_tables: set[str] = set()

        for pipeline_name in pipelines:
            try:
                config = load_pipeline_config(pipeline_name)
                if config.silver_table:
                    silver_tables.add(config.silver_table)
                if config.gold_table:
                    gold_tables.add(config.gold_table)
            except FileNotFoundError:
                self.logger.warning(
                    "Config not found for pipeline",
                    pipeline_name=pipeline_name,
                )

        tables: list[tuple[str, str]] = []
        if layer in ("all", "silver"):
            tables.extend((t, "silver") for t in sorted(silver_tables))
        if layer in ("all", "gold"):
            tables.extend((t, "gold") for t in sorted(gold_tables))

        return tables

    async def vacuum_table(
        self,
        table_name: str,
        layer: str,
        retention_days: int,
        dry_run: bool,
    ) -> TableVacuumResult:
        """Vacuum a single table and return structured result.

        Args:
            table_name: Name of the table to vacuum.
            layer: Medallion layer (silver/gold).
            retention_days: Minimum age of files to remove.
            dry_run: If True, only report what would be removed.

        Returns:
            TableVacuumResult with operation outcome.
        """
        try:
            files_removed = await self.lifecycle.vacuum(
                table=table_name,
                retention_days=retention_days,
                dry_run=dry_run,
            )
            return TableVacuumResult(
                table_name=table_name,
                layer=layer,
                files_removed=files_removed,
                error=None,
            )
        except Exception as e:
            self.logger.error(
                "Vacuum failed for table",
                table_name=table_name,
                layer=layer,
                error=str(e),
            )
            return TableVacuumResult(
                table_name=table_name,
                layer=layer,
                files_removed=0,
                error=str(e),
            )

    async def vacuum_all(
        self,
        tables: list[tuple[str, str]],
        retention_days: int,
        dry_run: bool,
    ) -> VacuumAllResult:
        """Vacuum multiple tables and aggregate results.

        Args:
            tables: List of (table_name, layer) tuples to vacuum.
            retention_days: Minimum age of files to remove.
            dry_run: If True, only report what would be removed.

        Returns:
            VacuumAllResult with aggregated statistics.
        """
        self.logger.info(
            "Starting vacuum-all operation",
            table_count=len(tables),
            retention_days=retention_days,
            dry_run=dry_run,
        )

        results: list[TableVacuumResult] = []
        for table_name, layer in tables:
            result = await self.vacuum_table(
                table_name=table_name,
                layer=layer,
                retention_days=retention_days,
                dry_run=dry_run,
            )
            results.append(result)

        vacuum_result = VacuumAllResult(
            results=tuple(results),
            dry_run=dry_run,
        )

        self.logger.info(
            "Vacuum-all completed",
            total_files_removed=vacuum_result.total_files_removed,
            success_count=vacuum_result.success_count,
            failed_count=len(vacuum_result.failed_tables),
            dry_run=dry_run,
        )

        return vacuum_result
