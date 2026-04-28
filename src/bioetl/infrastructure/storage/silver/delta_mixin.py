"""Delta operation helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterDeltaMixin"]

from typing import TYPE_CHECKING

from bioetl.infrastructure.storage.delta.resilience import SilverMergeResiliencePolicy
from bioetl.infrastructure.storage.silver.operations.delta_operations import (
    _SilverDeltaOperationFacade,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class SilverWriterDeltaMixin(_SilverDeltaOperationFacade):
    """Mixin with Delta write/merge operations."""

    logger: LoggerPort
    _metrics: MetricsPort | None
    _merge_resilience_policy: SilverMergeResiliencePolicy
