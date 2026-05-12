"""Workflow execution orchestration with manifest, ledger, state, and locking."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial
from uuid import uuid4

from bioetl.application.services.control_plane.workflow_execution_preparation import (
    prepare_workflow_execution,
)
from bioetl.application.services.control_plane.workflow_execution_recording import (
    WorkflowExecutionRecorder,
    record_step_completed,
    record_step_started,
    record_transform_commit,
    record_workflow_finished,
    record_workflow_started,
)
from bioetl.application.services.control_plane.workflow_ledger_service import (
    WorkflowLedgerService,
)
from bioetl.application.services.control_plane.workflow_manifest_service import (
    WorkflowManifestService,
)
from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowRunnerService,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.control_plane import WorkflowManifest
from bioetl.domain.ports import (
    LockPort,
    WorkflowExecutionStatePort,
    WorkflowLedgerPort,
)
from bioetl.domain.types import RunID
from bioetl.domain.workflow import (
    WorkflowConfig,
    WorkflowStepConfig,
)

__all__ = ["WorkflowExecutionService", "WorkflowLedgerFactory"]

WorkflowLedgerFactory = Callable[
    [WorkflowLedgerPort, WorkflowManifest],
    WorkflowLedgerService,
]


@dataclass(slots=True)
class WorkflowExecutionService:
    """Orchestrate workflow execution around durable control-plane artifacts."""

    workflow_runner: WorkflowRunnerService
    manifest_service: WorkflowManifestService
    workflow_ledger_port: WorkflowLedgerPort
    workflow_ledger_factory: WorkflowLedgerFactory
    workflow_state_port: WorkflowExecutionStatePort
    workflow_lock_port: LockPort
    now_factory: Callable[[], datetime] = current_utc_time
    run_id_factory: Callable[[], RunID] = lambda: RunID(uuid4())

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        launch_context: dict[str, object] | None = None,
        resume_last: bool = False,
        force_steps: tuple[str, ...] = (),
        repair_steps: tuple[str, ...] = (),
        incremental: bool = False,
    ) -> WorkflowRunExecutionResult:
        """Execute a workflow with durable manifest, ledger, state, and lock."""
        resolved_launch_context = _resolve_launch_context(
            launch_context=launch_context,
            resume_last=resume_last,
            force_steps=force_steps,
            repair_steps=repair_steps,
        )
        prepared = prepare_workflow_execution(
            config=config,
            launch_context=resolved_launch_context,
            resume_last=resume_last,
            force_steps=force_steps,
            repair_steps=repair_steps,
            manifest_service=self.manifest_service,
            workflow_state_port=self.workflow_state_port,
            now_factory=self.now_factory,
            run_id_factory=self.run_id_factory,
            incremental=incremental,
        )
        ledger = self.workflow_ledger_factory(
            self.workflow_ledger_port,
            prepared.manifest,
        )
        lock_key = _workflow_lock_key(config)
        await _acquire_workflow_lock(
            lock_port=self.workflow_lock_port,
            lock_key=lock_key,
            workflow_name=config.name,
            owner_id=prepared.manifest.workflow_run_id,
        )
        try:
            return await _run_locked_workflow(
                runner=self.workflow_runner,
                recorder=WorkflowExecutionRecorder(
                    ledger=ledger,
                    state_port=self.workflow_state_port,
                    state=prepared.state,
                ),
                prepared_manifest=prepared.manifest,
                completed_step_ids=prepared.completed_step_ids,
                completed_transform_fingerprints=(
                    prepared.completed_transform_fingerprints
                ),
                config=prepared.config,
                resumed=prepared.resumed,
                repair_steps=repair_steps,
                force_steps=force_steps,
                now_factory=self.now_factory,
                incremental=incremental,
            )
        finally:
            await self.workflow_lock_port.release(
                lock_key,
                prepared.manifest.workflow_run_id,
                exclusive=True,
            )


def _resolve_launch_context(
    *,
    launch_context: dict[str, object] | None,
    resume_last: bool,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> dict[str, object]:
    resolved_launch_context = dict(launch_context or {})
    resolved_launch_context["resume_last"] = resume_last
    resolved_launch_context["force_steps"] = list(force_steps)
    resolved_launch_context["repair_steps"] = list(repair_steps)
    return resolved_launch_context


def _workflow_lock_key(config: WorkflowConfig) -> str:
    return f"workflow:{config.name}"


def _extract_incremental_metadata(
    config: WorkflowConfig,
) -> tuple[int | None, int | None]:
    """Extract start_offset and limit from the first pipeline step.

    These values are saved in state for the next incremental run.
    If start_offset is None, treat it as 0 for incremental tracking.
    """
    for step in config.steps:
        if isinstance(step, WorkflowStepConfig):
            offset = step.run_options.start_offset
            limit = step.run_options.limit
            # Treat None as 0 for incremental tracking
            if offset is None:
                offset = 0
            print(f"DEBUG _extract_incremental_metadata: offset={offset}, limit={limit}")
            return (offset, limit)
    print("DEBUG _extract_incremental_metadata: no pipeline steps found")
    return (None, None)


async def _acquire_workflow_lock(
    *,
    lock_port: LockPort,
    lock_key: str,
    workflow_name: str,
    owner_id: RunID,
) -> None:
    token = await lock_port.acquire(
        lock_key,
        owner_id,
        wait=False,
        exclusive=True,
    )
    if token is None:
        raise RuntimeError(
            f"Workflow '{workflow_name}' is already running inside the current "
            "local runtime boundary"
        )


async def _run_locked_workflow(
    *,
    runner: WorkflowRunnerService,
    recorder: WorkflowExecutionRecorder,
    prepared_manifest: WorkflowManifest,
    completed_step_ids: frozenset[str],
    completed_transform_fingerprints: dict[str, str],
    config: WorkflowConfig,
    resumed: bool,
    repair_steps: tuple[str, ...],
    force_steps: tuple[str, ...],
    now_factory: Callable[[], datetime],
    incremental: bool = False,
) -> WorkflowRunExecutionResult:
    if not resumed:
        recorder.ledger.record_manifest_created(prepared_manifest)
    record_workflow_started(
        recorder,
        resumed=resumed,
        repair_steps=repair_steps,
        force_steps=force_steps,
    )
    result = await runner.run_workflow(
        config,
        completed_step_ids=completed_step_ids,
        completed_transform_fingerprints=completed_transform_fingerprints,
        step_started_callback=partial(record_step_started, recorder),
        step_completed_callback=partial(record_step_completed, recorder),
        transform_commit_callback=partial(record_transform_commit, recorder),
    )

    # Extract offset/limit for saving only if incremental is enabled
    last_offset, last_limit = (None, None)
    if incremental:
        last_offset, last_limit = _extract_incremental_metadata(config)

    record_workflow_finished(
        recorder,
        result,
        completed_at=now_factory(),
        last_start_offset=last_offset,
        last_limit=last_limit,
    )
    return replace(
        result,
        workflow_run_id=str(prepared_manifest.workflow_run_id),
        manifest_id=prepared_manifest.manifest_id,
        execution_fingerprint=prepared_manifest.execution_fingerprint,
        resumed=resumed,
    )
