"""Public resource-management composition API."""

from __future__ import annotations

from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
from bioetl.composition._resource_management import (
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    "get_quarantine_manager",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

