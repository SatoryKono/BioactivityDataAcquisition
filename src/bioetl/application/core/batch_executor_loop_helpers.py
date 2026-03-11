"""Internal helper functions for batch extraction loop orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService


__all__ = [
    "BatchExtractionLoopState",
    "append_record_and_update_batch_size",
    "build_batch_progress_payload",
    "build_periodic_checkpoint_payload",
    "build_shutdown_checkpoint_payload",
    "build_start_index",
    "create_batch_extraction_loop_state",
    "reset_batch_after_flush",
    "should_flush_batch",
]


@dataclass(slots=True)
class BatchExtractionLoopState:
    """Mutable state held across the extraction loop."""

    current_batch_size: int
    check_interval: int
    batch: list[BronzeRecord] = field(default_factory=list)


def create_batch_extraction_loop_state(
    *,
    batch_size: int,
    check_interval: int,
) -> BatchExtractionLoopState:
    """Create extraction loop state with initial sizing parameters."""
    return BatchExtractionLoopState(
        current_batch_size=batch_size,
        check_interval=check_interval,
    )


def append_record_and_update_batch_size(
    *,
    loop_state: BatchExtractionLoopState,
    raw_record: BronzeRecord,
    memory_manager: BatchMemoryManagerService,
    records_fetched: int,
) -> None:
    """Append one raw record and update adaptive batch size if needed."""
    loop_state.batch.append(raw_record)
    loop_state.current_batch_size = memory_manager.check_pressure(
        loop_state.current_batch_size,
        loop_state.check_interval,
        records_fetched,
    )


def should_flush_batch(loop_state: BatchExtractionLoopState) -> bool:
    """Return whether the accumulated batch reached the current flush size."""
    return len(loop_state.batch) >= loop_state.current_batch_size


def reset_batch_after_flush(
    *,
    loop_state: BatchExtractionLoopState,
    memory_manager: BatchMemoryManagerService,
) -> None:
    """Reset batch buffer and let adaptive sizing recover if pressure eased."""
    loop_state.batch = []
    loop_state.current_batch_size = memory_manager.maybe_recover(
        loop_state.current_batch_size
    )


def build_start_index(*, records_fetched: int, batch: list[BronzeRecord]) -> int:
    """Build absolute start index for the current batch buffer."""
    return records_fetched - len(batch)


def build_batch_progress_payload(
    *,
    records_fetched: int,
    records_bronze: int,
    records_silver: int,
    records_filtered_out: int,
) -> dict[str, int]:
    """Build progress payload for progress-service reporting."""
    return {
        "records_fetched": records_fetched,
        "records_bronze": records_bronze,
        "records_silver": records_silver,
        "records_filtered_out": records_filtered_out,
    }


def build_shutdown_checkpoint_payload(
    *,
    records_fetched: int,
    resume_offset: int,
) -> dict[str, int]:
    """Build payload for immediate shutdown checkpoint persistence."""
    return {
        "records_fetched": records_fetched,
        "resume_offset": resume_offset,
    }


def build_periodic_checkpoint_payload(
    *,
    records_fetched: int,
    resume_offset: int,
    checkpoint_interval: int,
) -> dict[str, int]:
    """Build payload for periodic checkpoint persistence."""
    return {
        "records_fetched": records_fetched,
        "resume_offset": resume_offset,
        "checkpoint_interval": checkpoint_interval,
    }
