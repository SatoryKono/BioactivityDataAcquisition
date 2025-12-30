"""Bootstrap functions for storage components.

Contains bootstrap functions for storage adapters, cleanup service,
and medallion lifecycle service. Used primarily by CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.factories.storage import StorageAdapter
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from bioetl.application.core.cleanup_service import CleanupService
    from bioetl.application.services import BronzeCleanupService, VacuumService
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

__all__ = [
    "bootstrap_bronze_cleanup_service",
    "bootstrap_cleanup",
    "bootstrap_lifecycle_service",
    "bootstrap_storage",
    "bootstrap_vacuum_service",
]


def bootstrap_storage() -> StorageAdapter:
    """Bootstrap a read-only storage adapter for CLI operations.

    Creates a minimal StorageAdapter suitable for preview operations.
    No CSV export is configured since this is for read-only inspection.
    Uses NoOpLogger since this is for CLI preview operations without observability.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Returns:
        StorageAdapter configured for the current environment.
    """
    settings = get_settings()
    noop_logger = NoOpLogger()
    noop_metrics = NoOpMetrics()
    noop_tracing = NoOpTracing()

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=settings.bronze_path,
            logger=noop_logger,
            metrics=noop_metrics,
            tracing=noop_tracing,
            save_json=False,
            json_path=None,
        ),
        silver_writer=SilverWriter(
            base_path=settings.silver_path,
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=None,
        ),
        gold_writer=GoldWriter(
            base_path=settings.gold_path,
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=None,
        ),
    )


def bootstrap_cleanup() -> CleanupService:
    """Bootstrap the cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Returns:
        CleanupService configured for the current environment.
    """
    from bioetl.application.core.cleanup_service import CleanupService

    storage = bootstrap_storage()
    noop_logger = NoOpLogger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_lifecycle_service() -> MedallionLifecycleService:
    """Bootstrap MedallionLifecycleService for CLI maintenance commands.

    Creates a MedallionLifecycleService for vacuum and archive operations.
    Used by CLI for `maintenance vacuum` and `maintenance archive` commands.

    Returns:
        MedallionLifecycleService configured for the current environment.
    """
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

    storage = bootstrap_storage()
    noop_logger = NoOpLogger()

    return MedallionLifecycleService(storage=storage, logger=noop_logger)


def bootstrap_bronze_cleanup_service() -> BronzeCleanupService:
    """Bootstrap BronzeCleanupService for CLI maintenance commands.

    Creates a BronzeCleanupService for Bronze layer retention cleanup.
    Used by CLI for `maintenance bronze-cleanup` command.

    Returns:
        BronzeCleanupService configured for the current environment.
    """
    from bioetl.application.services import BronzeCleanupService

    storage = bootstrap_storage()
    noop_logger = NoOpLogger()

    return BronzeCleanupService(storage=storage, logger=noop_logger)


def bootstrap_vacuum_service() -> VacuumService:
    """Bootstrap VacuumService for CLI maintenance commands.

    Creates a VacuumService for batch vacuum operations.
    Used by CLI for `maintenance vacuum-all` command.

    Returns:
        VacuumService configured for the current environment.
    """
    from bioetl.application.services import VacuumService

    lifecycle = bootstrap_lifecycle_service()
    noop_logger = NoOpLogger()

    # Create table collector that queries the registry (DI pattern)
    table_collector = _create_table_collector(noop_logger)

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector(
    logger: NoOpLogger,
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
    from bioetl.composition.entrypoints import load_pipeline_config
    from bioetl.composition.registry import get_default_registry

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
