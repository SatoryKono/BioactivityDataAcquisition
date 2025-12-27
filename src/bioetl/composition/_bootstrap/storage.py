"""Bootstrap functions for storage components.

Contains bootstrap functions for storage adapters, cleanup service,
and medallion lifecycle service. Used primarily by CLI operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.storage import StorageAdapter
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    from bioetl.application.core.cleanup_service import CleanupService
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )

__all__ = [
    "bootstrap_cleanup",
    "bootstrap_lifecycle_service",
    "bootstrap_storage",
]


def bootstrap_storage() -> StorageAdapter:
    """Bootstrap a read-only storage adapter for CLI operations.

    Creates a minimal StorageAdapter suitable for preview operations.
    No CSV export is configured since this is for read-only inspection.
    Uses NoOpLogger since this is for CLI preview operations without observability.

    Returns:
        StorageAdapter configured for the current environment.
    """
    settings = get_settings()
    noop_logger = NoOpLogger()
    noop_metrics = NoOpMetrics()

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=settings.bronze_path,
            logger=noop_logger,
            metrics=noop_metrics,
            save_json=False,
            json_path=None,
        ),
        silver_writer=DeltaWriter(
            base_path=settings.silver_path,
            logger=noop_logger,
            csv_exporter=None,
        ),
        gold_writer=GoldWriter(
            base_path=settings.gold_path,
            logger=noop_logger,
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
