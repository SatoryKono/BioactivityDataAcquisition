"""Bootstrap functions for storage adapter assembly.

Provides storage adapter creation for both CLI preview operations and
composite pipeline execution. This is a shared building block.

Note:
    This function uses NoOpLogger internally as observability is not
    required for storage adapter assembly. The actual observability
    is provided at a higher level (BatchWriter, RecordProcessor).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bioetl.composition.factories.storage import StorageAdapter
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.domain.ports import NoOpMetrics, NoOpTracing
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    # Deprecated alias (backward compatibility)
    "bootstrap_storage",
    # Canonical name (use this)
    "bootstrap_storage_adapter",
]


def bootstrap_storage_adapter(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Create a storage adapter for CLI and composite pipeline operations.

    Creates a StorageAdapter suitable for preview operations and composite
    pipelines. CSV export is disabled by default for read-only inspection
    but can be enabled for composite pipelines that need CSV output.

    Uses NoOpLogger since this is for CLI preview operations without observability.

    Layer: Returns infrastructure adapter (StorageAdapter) containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
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


def bootstrap_storage(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Bootstrap a storage adapter for CLI and composite pipeline operations.


    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
    return bootstrap_storage_adapter(enable_csv_export=enable_csv_export)
