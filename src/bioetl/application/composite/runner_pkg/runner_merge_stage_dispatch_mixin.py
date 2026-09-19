# Host attrs/methods provided by concrete composition (PD2 W1).
"""Merge-stage dispatch stubs and recording seams for CompositePipelineRunner."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
)
from bioetl.application.composite.runtime_models import (
    CompositeMergerProtocol,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.ports import LoggerPort

__all__ = ["_CompositeRunnerMergeStageDispatchMixin"]


class _CompositeRunnerMergeStageDispatchMixin:
    """Declaration stubs, dispatchers, and recording seams for merge."""

    _runtime: CompositeRuntimeConfig
    _fsm: FSMStateHelperService
    _logger: LoggerPort
    _config: CompositeConfig
    _run_id_str: str
    _merger: CompositeMergerProtocol
    _checkpoint_manager: CompositeCheckpointService

    async def _save_checkpoint_safe(
        self: _CompositeRunnerMergeStageHostProtocol,
        state: CompositeCheckpointState,
        operation: str,
    ) -> bool:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

    async def _generate_dq_reports(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

    async def _write_cv_quarantine(
        self: _CompositeRunnerMergeStageHostProtocol,
        merge_result: MergeResult,
    ) -> None:  # pragma: no cover - declaration-only contract (#10534, review 2026-12-31)
        raise NotImplementedError

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
