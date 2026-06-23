"""Progress and checkpoint helpers for batch extraction loops."""

from __future__ import annotations

__all__ = [
    "_BatchCheckpointRecoveryProtocol",
    "_BatchProgressReporterProtocol",
    "_BatchProgressSnapshot",
    "build_batch_progress_payload",
    "build_periodic_checkpoint_payload",
    "build_shutdown_checkpoint_payload",
    "ensure_extraction_not_shutdown",
    "report_batch_progress",
    "save_periodic_checkpoint_for_loop",
]

from collections.abc import Awaitable
from typing import Protocol

from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError


class _BatchProgressReporterProtocol(Protocol):
    """Minimal progress reporting contract required by extraction loop helpers."""

    def report_progress(
        self,
        *,
        records_fetched: int,
        records_bronze: int,
        records_silver: int,
        records_filtered_out: int,
    ) -> None: ...


class _BatchProgressSnapshot(Protocol):
    """Minimal counter snapshot used for progress reporting."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_filtered_out: int


class _BatchCheckpointRecoveryProtocol(Protocol):
    """Minimal checkpoint contract required by extraction loop helpers."""

    def save_checkpoint_now(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
    ) -> Awaitable[None]: ...

    def save_periodic_checkpoint(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        checkpoint_interval: int,
    ) -> Awaitable[None]: ...


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


def report_batch_progress(
    *,
    progress_service: _BatchProgressReporterProtocol,
    state: _BatchProgressSnapshot,
) -> None:
    """Report the current extraction counters through the progress service."""
    progress_service.report_progress(
        **build_batch_progress_payload(
            records_fetched=state.records_fetched,
            records_bronze=state.records_bronze,
            records_silver=state.records_silver,
            records_filtered_out=state.records_filtered_out,
        )
    )


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


async def ensure_extraction_not_shutdown(
    *,
    shutdown_requested: bool,
    checkpoint_recovery_service: _BatchCheckpointRecoveryProtocol,
    records_fetched: int,
    resume_offset: int,
) -> None:
    """Persist shutdown checkpoint and raise when extraction is asked to stop."""
    if not shutdown_requested:
        return
    await checkpoint_recovery_service.save_checkpoint_now(
        **build_shutdown_checkpoint_payload(
            records_fetched=records_fetched,
            resume_offset=resume_offset,
        )
    )
    raise PipelineShutdownError("Shutdown during extraction")


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


async def save_periodic_checkpoint_for_loop(
    *,
    checkpoint_recovery_service: _BatchCheckpointRecoveryProtocol,
    records_fetched: int,
    resume_offset: int,
    checkpoint_interval: int,
) -> None:
    """Persist the periodic checkpoint payload for the extraction loop."""
    await checkpoint_recovery_service.save_periodic_checkpoint(
        **build_periodic_checkpoint_payload(
            records_fetched=records_fetched,
            resume_offset=resume_offset,
            checkpoint_interval=checkpoint_interval,
        )
    )
