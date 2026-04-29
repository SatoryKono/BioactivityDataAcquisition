"""Bootstrap functions for storage adapter assembly.

Provides storage adapter creation for both CLI preview operations and
composite pipeline execution. This is a shared building block.

Note:
    This function uses NoOpLogger internally as observability is not
    required for storage adapter assembly. The actual observability
    is provided at a higher level (BatchWriter, RecordProcessor).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.bootstrap.cli.noop import create_noop_observability_bundle
from bioetl.composition.factories.storage import StorageBundle
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import Settings, get_settings
from bioetl.infrastructure.control_plane import FileLineageStore
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = [
    "bootstrap_storage_adapter",
]


def _create_composite_metadata_services(
    *,
    settings: Settings,
    output_dir: Path,
    logger: LoggerPort,
    metrics: MetricsPort,
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
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=current_utc_time(),
        pipeline_name="composite",
        provider="composite",
        entity="merged",
    )
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


def bootstrap_storage_adapter(*, enable_csv_export: bool = False) -> StorageBundle:
    """Create a storage adapter for CLI and composite pipeline operations.

    Creates a StorageBundle suitable for preview operations and composite
    pipelines. CSV export is disabled by default for read-only inspection
    but can be enabled for composite pipelines that need CSV output.

    Uses NoOpLogger since this is for CLI preview operations without observability.

    Layer: Returns infrastructure adapter (StorageBundle) containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageBundle configured for the current environment.
    """
    settings = get_settings()
    noop_logger, noop_metrics, noop_tracing = create_noop_observability_bundle()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(settings.data_dir) / "output"
    (
        metadata_writer,
        lineage_store,
        metadata_coordinator,
        merge_resilience_policy,
    ) = _create_composite_metadata_services(
        settings=settings,
        output_dir=output_dir,
        logger=noop_logger,
        metrics=noop_metrics,
    )
    silver_csv_exporter, gold_csv_exporter = _create_csv_exporters(
        output_dir=output_dir,
        logger=noop_logger,
        enable_csv_export=enable_csv_export,
    )

    return StorageBundle(
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
            lineage_store=lineage_store,
            merge_resilience_policy=merge_resilience_policy,
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=gold_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        ),
    )
