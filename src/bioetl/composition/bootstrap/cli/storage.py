"""Bootstrap functions for storage-related CLI operations.

Contains bootstrap functions for maintenance services:
- CleanupService: Preview and execute cleanup operations
- MedallionLifecycleService: Vacuum and archive Delta tables
- BronzeCleanupService: Bronze layer retention cleanup
- VacuumService: Batch vacuum operations
- ExportService: Export Delta tables to various formats

Note:
    Uses NoOp observability since these are CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.core.cleanup_service import CleanupService
from bioetl.application.services import (
    BronzeCleanupService,
    ExportService,
    VacuumService,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.registry import get_default_registry
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "bootstrap_bronze_cleanup_service",
    # Deprecated alias (backward compatibility)
    "bootstrap_cleanup",
    # Canonical name (use this)
    "bootstrap_cleanup_service",
    "bootstrap_export_service",
    "bootstrap_lifecycle_service",
    "bootstrap_vacuum_service",
]


def bootstrap_cleanup_service() -> CleanupService:
    """Create a cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Layer: Returns application service (CleanupService).

    Returns:
        CleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_cleanup() -> CleanupService:
    """Bootstrap the cleanup service for CLI operations.

    .. deprecated::
        Use :func:`bootstrap_cleanup_service` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Returns:
        CleanupService configured for the current environment.
    """
    return bootstrap_cleanup_service()


def bootstrap_lifecycle_service() -> MedallionLifecycleService:
    """Bootstrap MedallionLifecycleService for CLI maintenance commands.

    Creates a MedallionLifecycleService for vacuum and archive operations.
    Used by CLI for `maintenance vacuum` and `maintenance archive` commands.

    Returns:
        MedallionLifecycleService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return MedallionLifecycleService(storage=storage, logger=noop_logger)


def bootstrap_bronze_cleanup_service() -> BronzeCleanupService:
    """Bootstrap BronzeCleanupService for CLI maintenance commands.

    Creates a BronzeCleanupService for Bronze layer retention cleanup.
    Used by CLI for `maintenance bronze-cleanup` command.

    Returns:
        BronzeCleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return BronzeCleanupService(storage=storage, logger=noop_logger)


def bootstrap_vacuum_service() -> VacuumService:
    """Bootstrap VacuumService for CLI maintenance commands.

    Creates a VacuumService for batch vacuum operations.
    Used by CLI for `maintenance vacuum-all` command.

    Returns:
        VacuumService configured for the current environment.
    """
    lifecycle = bootstrap_lifecycle_service()
    noop_logger = create_noop_logger()

    # Create table collector that queries the registry (DI pattern)
    table_collector = _create_table_collector(noop_logger)

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector(
    logger: LoggerPort,
) -> Callable[[str], list[tuple[str, str]]]:
    """Create a table collector function for VacuumService.

    This function queries the pipeline registry and config loader
    to collect silver/gold tables. It lives in composition layer
    to maintain proper dependency direction (application -> domain <- composition).

    Args:
        logger: Logger for warnings when configs are not found.

    Returns:
        Callable that collects tables for a given layer.
    """

    def collect_tables(layer: str) -> list[tuple[str, str]]:
        """Collect tables from all registered pipelines.

        Args:
            layer: Which layer to collect - "all", "silver", or "gold".

        Returns:
            List of (table_name, layer) tuples sorted alphabetically.
        """
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
                logger.warning(
                    "Config not found for pipeline",
                    pipeline_name=pipeline_name,
                )

        tables: list[tuple[str, str]] = []
        if layer in ("all", "silver"):
            tables.extend((t, "silver") for t in sorted(silver_tables))
        if layer in ("all", "gold"):
            tables.extend((t, "gold") for t in sorted(gold_tables))

        return tables

    return collect_tables


def bootstrap_export_service() -> ExportService:
    """Bootstrap ExportService for CLI export commands.

    Creates an ExportService for exporting Delta Lake tables to
    CSV, XLSX, and TSV formats.

    Returns:
        ExportService configured for the current environment.
    """
    settings = get_settings()
    noop_logger = create_noop_logger()

    # Use data/output/ subdirectory for actual data paths (matches pipeline configs)
    # The pipeline configs use data/output/silver, data/output/gold
    output_dir = Path(settings.data_dir) / "output"
    silver_path = output_dir / "silver"
    gold_path = output_dir / "gold"

    # Create Delta reader for Silver and Gold paths
    reader = DeltaReader(
        base_path=silver_path,  # Base path for relative paths
        logger=noop_logger,
    )

    return ExportService(
        reader=reader,
        logger=noop_logger,
        silver_path=silver_path,
        gold_path=gold_path,
        export_path=output_dir / "exports",
    )
