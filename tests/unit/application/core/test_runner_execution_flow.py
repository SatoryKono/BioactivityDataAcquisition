"""Focused tests for ordinary runner execution flow orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from bioetl.application.core import runner_execution_flow
from bioetl.domain.control_plane.run_ledger import ORDINARY_RUN_LEDGER_STAGE_NAMES


class _ExecutionHost:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.started: list[str] = []
        self.completed: list[str] = []
        self.offset = 17
        self._config = SimpleNamespace(pipeline_name="test_runner_pipeline")
        self._runtime = SimpleNamespace(limit=11, query="kinase")
        self._services = SimpleNamespace()
        self._executor = SimpleNamespace(
            execute=self._execute_pipeline,
            get_dq_context=lambda: "dq-context",
        )
        self._checkpoint_manager = SimpleNamespace(
            delete_checkpoint=self._delete_checkpoint,
        )
        self._preflight_service = SimpleNamespace(
            validate_infrastructure=self._validate_infrastructure,
        )
        self._postrun_service = SimpleNamespace(run=self._run_postrun)
        self._lifecycle_service = SimpleNamespace(
            prepare_for_run=self._prepare_for_run,
        )
        self.execute_calls: list[tuple[int | None, int | None, str | None]] = []
        self.postrun_calls: list[tuple[object, object]] = []

    async def _resolve_execution_offset(self) -> int | None:
        self.order.append("resolve_offset")
        return self.offset

    def _record_stage_started(self, stage: str) -> None:
        self.started.append(stage)
        self.order.append(f"start:{stage}")

    def _record_stage_completed(self, stage: str) -> None:
        self.completed.append(stage)
        self.order.append(f"complete:{stage}")

    async def _validate_infrastructure(self, services: object) -> None:
        assert services is self._services
        self.order.append("validate_infrastructure")

    async def _prepare_for_run(self, *, config: object, runtime: object) -> None:
        assert config is self._config
        assert runtime is self._runtime
        self.order.append("prepare_medallion_layers")

    async def _execute_pipeline(
        self,
        *,
        limit: int | None,
        query: str | None,
        offset: int | None,
    ) -> None:
        self.execute_calls.append((limit, offset, query))
        self.order.append("execute_pipeline")

    async def _run_postrun(self, *, executor: object, dq_context: object) -> None:
        self.postrun_calls.append((executor, dq_context))
        self.order.append("postrun")

    async def _delete_checkpoint(self) -> None:
        self.order.append("checkpoint_finalize")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_managed_pipeline_preserves_canonical_stage_order() -> None:
    host = _ExecutionHost()

    await runner_execution_flow.run_managed_pipeline(cast(Any, host))

    assert host.started == list(ORDINARY_RUN_LEDGER_STAGE_NAMES)
    assert host.completed == list(ORDINARY_RUN_LEDGER_STAGE_NAMES)
    assert host.order == [
        "start:preflight",
        "validate_infrastructure",
        "complete:preflight",
        "start:prepare_medallion_layers",
        "prepare_medallion_layers",
        "complete:prepare_medallion_layers",
        "resolve_offset",
        "start:execute_pipeline",
        "execute_pipeline",
        "complete:execute_pipeline",
        "start:postrun",
        "postrun",
        "complete:postrun",
        "start:checkpoint_finalize",
        "checkpoint_finalize",
        "complete:checkpoint_finalize",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_execution_cycle_passes_resolved_offset_to_executor() -> None:
    host = _ExecutionHost()

    await runner_execution_flow.run_execution_cycle(cast(Any, host))

    assert host.execute_calls == [(11, 17, "kinase")]
    assert host.postrun_calls == [(host._executor, "dq-context")]
    assert host.started == list(ORDINARY_RUN_LEDGER_STAGE_NAMES[2:])
    assert host.completed == list(ORDINARY_RUN_LEDGER_STAGE_NAMES[2:])
