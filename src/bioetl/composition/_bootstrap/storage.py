"""Bootstrap functions for storage components.

Contains bootstrap functions for storage adapters, cleanup service,
and medallion lifecycle service. Used primarily by CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
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
    from bioetl.application.services import (
        BronzeCleanupService,
        ExportService,
        VacuumService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

__all__ = [
    "bootstrap_bronze_cleanup_service",
    "bootstrap_cleanup",
    "bootstrap_export_service",
    "bootstrap_lifecycle_service",
    "bootstrap_storage",
    "bootstrap_vacuum_service",
]


def bootstrap_storage(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Bootstrap a storage adapter for CLI and composite pipeline operations.

    Creates a StorageAdapter suitable for preview operations and composite
    pipelines. CSV export is disabled by default for read-only inspection
    but can be enabled for composite pipelines that need CSV output.

    Uses NoOpLogger since this is for CLI preview operations without observability.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.types import RunID, RunType
    from bioetl.domain.value_objects.run_context import RunContext
    from bioetl.infrastructure.export.csv_exporter import CsvExporter
    from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

    settings = get_settings()
    noop_logger = NoOpLogger()
    noop_metrics = NoOpMetrics()
    noop_tracing = NoOpTracing()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(settings.data_dir) / "output"

    # Create metadata services for composite pipelines
    metadata_writer = MetadataWriter(logger=noop_logger)
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        pipeline_name="composite",
        provider="composite",
        entity="merged",
    )
    metadata_coordinator = MetadataCoordinator(run_context=run_context)

    # Create CSV exporters if enabled (for composite pipelines)
    silver_csv_exporter = None
    gold_csv_exporter = None
    if enable_csv_export:
        silver_csv_exporter = CsvExporter(
            base_path=str(output_dir / "silver"),
            logger=noop_logger,
        )
        gold_csv_exporter = CsvExporter(
            base_path=str(output_dir / "gold"),
            logger=noop_logger,
        )

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=output_dir / "bronze",  # data/output/bronze
            logger=noop_logger,
            metrics=noop_metrics,
            tracing=noop_tracing,
            save_json=False,
            json_path=None,
        ),
        silver_writer=SilverWriter(
            base_path=output_dir / "silver",  # data/output/silver
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=silver_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=gold_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
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
    table_collector = _create_table_collector()

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector() -> Callable[[str], list[tuple[str, str]]]:
    """Create a table collector function for VacuumService.

    This function queries the pipeline registry and config loader
    to collect silver/gold tables. It lives in composition layer
    to maintain proper dependency direction (application -> domain <- composition).

    Returns:
        Callable that collects tables for a given layer.

    Raises:
        ValueError: If config file for a registered pipeline is not found.
    """
    from bioetl.composition.entrypoints import load_pipeline_config
    from bioetl.composition.registry import get_default_registry

    def collect_tables(layer: str) -> list[tuple[str, str]]:
        """Collect tables from all registered pipelines.

        Args:
            layer: Which layer to collect - "all", "silver", or "gold".

        Returns:
            List of (table_name, layer) tuples sorted alphabetically.

        Raises:
            ValueError: If config file for a registered pipeline is not found.
        """
        registry = get_default_registry()
        pipelines = registry.list_pipelines()

        silver_tables: set[str] = set()
        gold_tables: set[str] = set()

        for pipeline_name in pipelines:
            config = load_pipeline_config(pipeline_name)
            if config.silver_table:
                silver_tables.add(config.silver_table)
            if config.gold_table:
                gold_tables.add(config.gold_table)

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
    from bioetl.application.services import ExportService
    from bioetl.infrastructure.storage.delta_reader import DeltaReader

    settings = get_settings()
    noop_logger = NoOpLogger()

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
