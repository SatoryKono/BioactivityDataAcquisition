"""Checkpoint payload builders for BatchCheckpointRecoveryService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService


def build_checkpoint_payload(
    total: int,
    memory_manager: BatchMemoryManagerService | None,
) -> CheckpointMetadata | int:
    """Build checkpoint payload, including memory trace when available."""
    if memory_manager is None:
        return total
    memory_trace = memory_manager.decision_trace_dicts()
    if not memory_trace:
        return total
    return CheckpointMetadata(
        records_processed=total,
        memory_decision_trace=memory_trace,
    )
