"""Bootstrap functions for runtime-safe storage bundle assembly.

Provides storage bundle creation for callers that already own runtime identity.
CLI preview operations must use ``composition.bootstrap.cli.storage`` wrappers
that create explicit preview-only run context before calling this module.

Note:
    This module must not generate run identity or wall-clock timestamps.
    The Composition Root caller owns those runtime decisions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.storage import StorageBundle
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from bioetl.infrastructure.config.settings_api import Settings, get_settings
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.value_objects.run_context import RunContext

__all__ = [
    "bootstrap_storage_adapter",
]


def _create_composite_metadata_services(
    *,
    settings: Settings,
    output_dir: Path,
    logger: LoggerPort,
    metrics: MetricsPort,
    run_context: RunContext,
) -> tuple[
    MetadataWriter,
    FileLineageStore,
    MetadataCoordinator,
    SilverMergeResiliencePolicy,
]:
    """Create shared metadata services and resilience policy for storage bootstrap."""
    atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    metadata_writer = MetadataWriter(
        logger=logger,
        atomic_replace_retry_policy=atomic_retry_policy,
        metrics=metrics,
    )
    lineage_store = FileLineageStore(base_path=output_dir / "control" / "lineage")
    return (
        metadata_writer,
        lineage_store,
        MetadataCoordinator(run_context=run_context),
        merge_resilience_policy,
    )


def _create_csv_exporters(
    *,
    output_dir: Path,
    logger: LoggerPort,
    enable_csv_export: bool,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for silver and gold layers."""
    if not enable_csv_export:
        return None, None
    return (
        CsvExporter(base_path=str(output_dir / "silver"), logger=logger),
        CsvExporter(base_path=str(output_dir / "gold"), logger=logger),
    )


def bootstrap_storage_adapter(
    *,
    run_context: RunContext,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    enable_csv_export: bool = False,
    settings: Settings | None = None,
) -> StorageBundle:
    """Create a storage bundle for callers with explicit runtime context.

    Layer: Returns a composition storage bundle containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        run_context: Explicit runtime identity and timestamp context owned by
            the caller.
        logger: LoggerPort wired by the caller.
        metrics: MetricsPort wired by the caller.
        tracing: TracingPort wired by the caller.
        enable_csv_export: If True, creates CsvExporters for Silver and Gold.
        settings: Optional Settings override for tests; defaults to get_settings().

    Returns:
        StorageBundle configured for the current environment.
    """
    effective_settings = settings if settings is not None else get_settings()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(effective_settings.data_dir) / "output"
    (
        metadata_writer,
        lineage_store,
        metadata_coordinator,
        merge_resilience_policy,
    ) = _create_composite_metadata_services(
        settings=effective_settings,
        output_dir=output_dir,
        logger=logger,
        metrics=metrics,
        run_context=run_context,
    )
    silver_csv_exporter, gold_csv_exporter = _create_csv_exporters(
        output_dir=output_dir,
        logger=logger,
        enable_csv_export=enable_csv_export,
    )

    return StorageBundle(
        bronze_writer=BronzeWriter(
            base_path=output_dir / "bronze",  # data/output/bronze
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            save_json=False,
            json_path=None,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
        silver_writer=SilverWriter(
            base_path=output_dir / "silver",  # data/output/silver
            logger=logger,
            tracing=tracing,
            csv_exporter=silver_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            merge_resilience_policy=merge_resilience_policy,
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=logger,
            tracing=tracing,
            csv_exporter=gold_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
    )
