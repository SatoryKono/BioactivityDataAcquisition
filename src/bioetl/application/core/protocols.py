"""
Callback protocols for the pipeline.
"""
from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol

from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BatchID


class TransformCallback(Protocol):
    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Awaitable[dict[str, Any] | None]: ...


class GoldFilterCallback(Protocol):
    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool: ...


class QuarantineManagerProtocol(Protocol):
    """Protocol for handling record quarantine."""

    async def quarantine_record(
        self,
        record: dict[str, Any],
        error: Exception,
        batch_id: BatchID,
    ) -> None:
        """Quarantine a failed record.

        Args:
            record: The record that failed processing.
            error: The exception that caused the failure.
            batch_id: ID of the batch being processed.
        """
        ...
