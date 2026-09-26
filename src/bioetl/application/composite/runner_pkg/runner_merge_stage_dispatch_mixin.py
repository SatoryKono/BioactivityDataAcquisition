# Host attrs/methods provided by concrete composition (PD2 W1).
"""Merge-stage dispatchers and recording seams for CompositePipelineRunner."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
)
from bioetl.domain.composite.result import MergeResult

__all__ = ["_CompositeRunnerMergeStageDispatchMixin"]


class _CompositeRunnerMergeStageDispatchMixin:
    """Dispatchers and recording seams for merge (host methods via Protocol/MRO)."""

    async def _call_save_checkpoint_safe(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:
        return await self._save_checkpoint_safe(state, operation)

    async def _call_generate_dq_reports(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        await self._generate_dq_reports(merge_result)

    async def _call_write_cv_quarantine(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        await self._write_cv_quarantine(merge_result)

    def _record_merge_stage_started(
        self: _CompositeRunnerMergeStageHostProtocol,
    ) -> None:
        """Default no-op seam for hosts without merge-stage ledger wiring."""

    def _record_merge_stage_completed(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Default no-op seam for tests or hosts without merge-stage ledger wiring."""
        del merge_result
