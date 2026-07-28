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
from typing import TYPE_CHECKING, cast
from uuid import NAMESPACE_URL, uuid5

from bioetl.application.core.lifecycle.cleanup_service import CleanupStorageProtocol
from bioetl.application.services.admin_runtime_api import CleanupService
from bioetl.application.services.bronze_cleanup_service import BronzeCleanupService
from bioetl.application.services.contract_migration_service import (
    ContractMigrationService,
)
from bioetl.application.services.export_service import ExportService
from bioetl.application.services.medallion.medallion_lifecycle import (
    MedallionLifecycleService,
    MedallionStorageProtocol,
)
from bioetl.application.services.vacuum_service import VacuumService
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.cli.config import bootstrap_config_service
from bioetl.composition.bootstrap.cli.noop import (
    create_noop_logger,
    create_noop_observability_bundle,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry_api import create_registry
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.ports import BronzeStoragePort
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.contract_registry_loader import (
    load_contract_registry_entries,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.export.export_catalog_adapter import ExportCatalogAdapter
from bioetl.infrastructure.export.export_writer_adapter import ExportWriterAdapter
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.time import SystemClock

__all__ = [
    "bootstrap_bronze_cleanup_service",
    "bootstrap_cleanup_service",
    "bootstrap_cli_storage_adapter",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_lifecycle_service",
    "bootstrap_vacuum_service",
]

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry


def _create_cli_preview_run_context() -> RunContext:
    """Create explicit CLI-only preview run context for maintenance storage."""
    started_at = current_utc_time()
    return RunContext(
        run_id=RunID(
            uuid5(
                NAMESPACE_URL,
                f"bioetl:cli-storage-preview:{started_at.isoformat()}",
            )
        ),
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        pipeline_name="cli-storage-preview",
        provider="cli",
        entity="maintenance",
    )


def bootstrap_cli_storage_adapter(*, enable_csv_export: bool = False) -> object:
    """Create a CLI-only storage bundle with explicit preview runtime context."""
    noop_logger, noop_metrics, noop_tracing = create_noop_observability_bundle()
    return bootstrap_storage_adapter(
        run_context=_create_cli_preview_run_context(),
        logger=noop_logger,
        metrics=noop_metrics,
        tracing=noop_tracing,
        enable_csv_export=enable_csv_export,
    )


def bootstrap_cleanup_service() -> CleanupService:
    """Create a cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Layer: Returns application service (CleanupService).

    Returns:
        CleanupService configured for the current environment.
    """
    storage = cast(CleanupStorageProtocol, bootstrap_cli_storage_adapter())
    noop_logger = create_noop_logger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_lifecycle_service() -> MedallionLifecycleService:
    """Bootstrap MedallionLifecycleService for CLI maintenance commands.

    Creates a MedallionLifecycleService for vacuum and archive operations.
    Used by CLI for `maintenance vacuum` and `maintenance archive` commands.

    Returns:
        MedallionLifecycleService configured for the current environment.
    """
    storage = cast(MedallionStorageProtocol, bootstrap_cli_storage_adapter())
    noop_logger = create_noop_logger()

    return MedallionLifecycleService(storage=storage, logger=noop_logger)


def bootstrap_bronze_cleanup_service() -> BronzeCleanupService:
    """Bootstrap BronzeCleanupService for CLI maintenance commands.

    Creates a BronzeCleanupService for Bronze layer retention cleanup.
    Used by CLI for `maintenance bronze-cleanup` command.

    Returns:
        BronzeCleanupService configured for the current environment.
    """
    storage = cast(BronzeStoragePort, bootstrap_cli_storage_adapter())
    noop_logger = create_noop_logger()

    return BronzeCleanupService(
        storage=storage,
        logger=noop_logger,
        clock=SystemClock(),
    )


def bootstrap_contract_migration_service(
    *,
    registry: PipelineRegistry | None = None,
) -> ContractMigrationService:
    """Bootstrap ContractMigrationService for maintenance planner commands."""
    noop_logger = create_noop_logger()
    config_service = bootstrap_config_service(registry=registry)
    return ContractMigrationService(
        logger=noop_logger,
        _pipeline_info_loader=config_service.validate_pipeline_config,
        _contract_policy_loader=load_pipeline_contract_policy,
        _registry_entries_loader=load_contract_registry_entries,
    )


def bootstrap_vacuum_service(
    *,
    registry: PipelineRegistry | None = None,
) -> VacuumService:
    """Bootstrap VacuumService for CLI maintenance commands.

    Creates a VacuumService for batch vacuum operations.
    Used by CLI for `maintenance vacuum-all` command.

    Args:
        registry: Optional explicit registry. When omitted, a fresh registered
            registry is built for the table collector.

    Returns:
        VacuumService configured for the current environment.
    """
    lifecycle = bootstrap_lifecycle_service()
    noop_logger = create_noop_logger()

    # Create table collector that queries the registry (DI pattern)
    table_collector = _create_table_collector(registry=registry)

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector(
    *,
    registry: PipelineRegistry | None = None,
) -> Callable[[str], list[tuple[str, str]]]:
    """Create a callable that gathers Silver/Gold table names from registry configs."""
    effective_registry = registry if registry is not None else create_registry()
    if registry is None:
        register_all_pipelines(registry=effective_registry)

    def collect_tables(layer: str) -> list[tuple[str, str]]:
        """Collect `(table_name, layer)` pairs for requested layer scope."""
        pipelines = effective_registry.list_pipelines()

        silver_tables: set[str] = set()
        gold_tables: set[str] = set()

        for pipeline_name in pipelines:
            pipeline_cfg = load_pipeline_config(pipeline_name)
            silver_table = (
                pipeline_cfg.silver_table
                or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
            )
            gold_table = (
                pipeline_cfg.gold_table
                or f"{pipeline_cfg.provider}.{pipeline_cfg.entity_type}"
            )
            if silver_table:
                silver_tables.add(silver_table)
            if gold_table:
                gold_tables.add(gold_table)

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
        catalog=ExportCatalogAdapter(),
        writer=ExportWriterAdapter(),
        logger=noop_logger,
        silver_path=silver_path,
        gold_path=gold_path,
        export_path=output_dir / "exports",
    )
