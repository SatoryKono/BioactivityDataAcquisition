"""Application services for cross-cutting concerns.

Implements RULES.md §4 - Application Layer services.
These services coordinate business logic and are injected into runners.

Administrative services for CLI operations:
- CheckpointService: Checkpoint listing, deletion, inspection
- QuarantineService: Quarantine inspection, replay, purge
- LockService: Lock management
- BronzeCleanupService: Bronze retention cleanup
- PipelineRunnerService: Universal pipeline execution
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
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.lock_service import (
    LockInfo,
    LockService,
)
from bioetl.application.services.medallion_lifecycle import (
    ClearResult,
    MedallionLifecycleService,
)
from bioetl.application.services.pipeline_runner_service import (
    PipelineNotFoundError,
    PipelineRunnerService,
    RunOptions,
    RunResult,
    RunStatus,
)
from bioetl.application.services.quarantine_service import (
    PurgeResult,
    QuarantineRecord,
    QuarantineService,
    ReplayResult,
)
from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)
from bioetl.application.services.vacuum_service import (
    TableCollectorPort,
    TableVacuumResult,
    VacuumAllResult,
    VacuumService,
)

__all__ = [
    "BronzeCleanupService",
    "CheckpointInfo",
    "CheckpointService",
    "CleanupResult",
    "ClearResult",
    "DataQualityService",
    "LockInfo",
    "LockService",
    "MedallionLifecycleService",
    "PipelineNotFoundError",
    "PipelineRunnerService",
    "PipelineShutdownError",
    "PurgeResult",
    "QuarantineRecord",
    "QuarantineService",
    "ReplayResult",
    "RunOptions",
    "RunResult",
    "RunStatus",
    "ShutdownReason",
    "ShutdownService",
    "TableCollectorPort",
    "TableVacuumResult",
    "VacuumAllResult",
    "VacuumService",
]
