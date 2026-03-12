"""Domain Aggregates.

Aggregates encapsulate business rules and protect invariants through
controlled APIs. Each aggregate is accessed only through its root entity.

Aggregates in BioETL:
- PipelineRun: Orchestration context with stage tracking
- Batch: Collection of records with consistent batch_id
- QuarantineEntry: Failed record with error context

All aggregates follow DDD principles:
1. Invariants are enforced internally
2. State changes only through aggregate methods
3. Domain events for inter-aggregate coordination
"""

from __future__ import annotations

from bioetl.domain.aggregates.batch import (
    Batch,
    BatchRecord,
    BatchStatus,
)
from bioetl.domain.aggregates.pipeline_run import (
    PipelineRun,
    PipelineRunState,
    StageResult,
    StageStatus,
)
from bioetl.domain.aggregates.quarantine_entry import (
    QuarantineEntry,
    QuarantineStatus,
)

__all__ = [
    "Batch",
    "BatchRecord",
    "BatchStatus",
    "PipelineRun",
    "PipelineRunState",
    "QuarantineEntry",
    "QuarantineStatus",
    "StageResult",
    "StageStatus",
]
