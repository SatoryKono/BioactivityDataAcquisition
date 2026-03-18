"""Stable application-level contracts used by BatchExecutor."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from bioetl.application.core.batch_processing_contracts import BatchProcessingOutcome
from bioetl.domain.types import BronzeRecord

_BatchResultT = TypeVar("_BatchResultT", covariant=True)


class _BatchResultBuilder(Protocol[_BatchResultT]):
    """Callable result factory for batch result projections."""

    def __call__(
        self,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> _BatchResultT: ...


@runtime_checkable
class PipelineProcessingPort(Protocol):
    """Contract for end-to-end processing of one assembled batch."""

    async def process_batch(
        self,
        *,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> BatchProcessingOutcome:
        """Process one assembled batch.

        Semantics:
        - performs Bronze write
        - performs transform, including quarantine side effects
        - performs Silver/Gold writes
        - emits batch-local metrics/tracing
        - raises on processing/write failures
        """
        ...


class BatchStateCommitPort(Protocol):
    """Applies successful batch outcome to executor-owned cumulative state."""

    def commit_successful_batch(
        self,
        *,
        state: object,
        records: list[BronzeRecord],
        outcome: BatchProcessingOutcome,
    ) -> None: ...

    def build_batch_result(
        self,
        *,
        state: object,
        batch_result_type: _BatchResultBuilder[_BatchResultT],
    ) -> _BatchResultT: ...

    def build_run_statistics(
        self,
        *,
        state: object,
    ) -> dict[str, int | list[str]]: ...
