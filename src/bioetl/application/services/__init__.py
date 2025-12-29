"""Application services for cross-cutting concerns.

Implements RULES.md §4 - Application Layer services.
These services coordinate business logic and are injected into runners.

Administrative services for CLI operations:
- CheckpointService: Checkpoint listing, deletion, inspection
- QuarantineService: Quarantine inspection, replay, purge
- LockService: Lock management
- BronzeCleanupService: Bronze retention cleanup
"""

from __future__ import annotations

from bioetl.application.services.bronze_cleanup_service import (
    BronzeCleanupService,
    CleanupResult,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from bioetl.application.services.lock_service import (
    LockInfo,
    LockService,
)
from bioetl.application.services.medallion_lifecycle import (
    ClearResult,
    MedallionLifecycleService,
)
from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)

__all__ = [
    # Medallion lifecycle
    "ClearResult",
    "MedallionLifecycleService",
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
]
