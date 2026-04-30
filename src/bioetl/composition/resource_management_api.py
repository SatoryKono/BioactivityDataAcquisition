"""Deprecated alias module for ``bioetl.composition.resources_api``."""

from __future__ import annotations

import warnings

from bioetl.composition.resources_api import (
    ArchiveOptions,
    VacuumOptions,
    archive_table,
    get_checkpoint_runtime_service,
    get_lifecycle_service,
    get_quarantine_runtime_service,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_runtime_service",
    "get_lifecycle_service",
    "get_quarantine_runtime_service",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

warnings.warn(
    (
        "`bioetl.composition.resource_management_api` is deprecated; "
        "use `bioetl.composition.resources_api`."
    ),
    DeprecationWarning,
    stacklevel=2,
)
