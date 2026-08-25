"""Workflow-owned orchestration with manifest, ledger, state, and locking."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial

from bioetl.application.runtime_clock import current_utc_time
from bioetl.application.services.control_plane.workflow.ledger_service import (
    WorkflowLedgerService,
)
from bioetl.application.services.workflow.control_plane.execution_incremental_metadata import (
    extract_incremental_metadata,
)
from bioetl.application.services.workflow.control_plane.execution_preparation import (
    prepare_workflow_execution,
)
from bioetl.application.services.workflow.control_plane.execution_recording import (
    WorkflowExecutionRecorder,
    record_step_completed,
    record_step_started,
    record_transform_commit,
    record_workflow_finished,
    record_workflow_started,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowRunnerService,
)
from bioetl.domain.control_plane import WorkflowManifest
from bioetl.domain.ports import (
    LockPort,
    WorkflowExecutionStatePort,
    WorkflowLedgerPort,
)
from bioetl.domain.types import RunID
from bioetl.domain.workflow import WorkflowConfig

__all__ = ["WorkflowExecutionService", "WorkflowLedgerFactory"]

WorkflowLedgerFactory = Callable[
    [WorkflowLedgerPort, WorkflowManifest],
    WorkflowLedgerService,
]


def _missing_run_id_factory() -> RunID:
    raise RuntimeError("workflow run_id_factory must be supplied by composition root")


@dataclass(slots=True)
class WorkflowExecutionService:
    """Orchestrate workflow execution around durable control-plane artifacts."""

    workflow_runner: WorkflowRunnerService
    manifest_service: object
    workflow_ledger_port: WorkflowLedgerPort
    workflow_ledger_factory: WorkflowLedgerFactory
    workflow_state_port: WorkflowExecutionStatePort
    workflow_lock_port: LockPort
    now_factory: Callable[[], datetime] = current_utc_time
    run_id_factory: Callable[[], RunID] = _missing_run_id_factory

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        launch_context: dict[str, object] | None = None,
        resume_last: bool = False,
        resume_manifest_id: str | None = None,
        resume_run_id: RunID | str | None = None,
        force_steps: tuple[str, ...] = (),
        repair_steps: tuple[str, ...] = (),
        incremental: bool = False,
    ) -> WorkflowRunExecutionResult:
        """Execute a workflow with durable manifest, ledger, state, and lock."""
        resolved_launch_context = _resolve_launch_context(
            launch_context=launch_context,
            resume_last=resume_last,
            resume_manifest_id=resume_manifest_id,
            resume_run_id=resume_run_id,
            force_steps=force_steps,
            repair_steps=repair_steps,
        )
        lock_key = _workflow_lock_key(config)
        lock_owner_id = self.run_id_factory()
        await _acquire_workflow_lock(
            lock_port=self.workflow_lock_port,
            lock_key=lock_key,
            workflow_name=config.name,
            owner_id=lock_owner_id,
        )
        try:
            prepared = prepare_workflow_execution(
                config=config,
                launch_context=resolved_launch_context,
                resume_last=resume_last,
                resume_manifest_id=resume_manifest_id,
                resume_run_id=resume_run_id,
                force_steps=force_steps,
                repair_steps=repair_steps,
                manifest_service=self.manifest_service,
                workflow_state_port=self.workflow_state_port,
                now_factory=self.now_factory,
                run_id_factory=lambda: lock_owner_id,
                incremental=incremental,
            )
            ledger = self.workflow_ledger_factory(
                self.workflow_ledger_port,
                prepared.manifest,
            )
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
                lock_owner_id,
                exclusive=True,
            )

    def record_expected_pipeline_metrics(self, config: WorkflowConfig) -> None:
        """Record planned pipeline scopes for workflow-backed selectors."""
        self.workflow_runner.record_expected_pipeline_metrics(config)


def _resolve_launch_context(
    *,
    launch_context: dict[str, object] | None,
    resume_last: bool,
    resume_manifest_id: str | None,
    resume_run_id: RunID | str | None,
    force_steps: tuple[str, ...],
    repair_steps: tuple[str, ...],
) -> dict[str, object]:
    resolved_launch_context = dict(launch_context or {})
    resolved_launch_context["resume_last"] = resume_last
    resolved_launch_context["resume_manifest_id"] = resume_manifest_id
    resolved_launch_context["resume_run_id"] = (
        str(resume_run_id) if resume_run_id is not None else None
    )
    resolved_launch_context["force_steps"] = list(force_steps)
    resolved_launch_context["repair_steps"] = list(repair_steps)
    return resolved_launch_context


def _workflow_lock_key(config: WorkflowConfig) -> str:
    return f"workflow:{config.name}"


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
        workflow_run_id=str(prepared_manifest.workflow_run_id),
        manifest_id=prepared_manifest.manifest_id,
        completed_step_ids=completed_step_ids,
        completed_transform_fingerprints=completed_transform_fingerprints,
        step_started_callback=partial(record_step_started, recorder),
        step_completed_callback=partial(record_step_completed, recorder),
        transform_commit_callback=partial(record_transform_commit, recorder),
        created_at_factory=now_factory,
    )

    if incremental:
        last_offset, last_limit = extract_incremental_metadata(config)
        record_workflow_finished(
            recorder,
            result,
            completed_at=now_factory(),
            last_start_offset=last_offset,
            last_limit=last_limit,
        )
    else:
        record_workflow_finished(
            recorder,
            result,
            completed_at=now_factory(),
        )
    return replace(
        result,
        workflow_run_id=str(prepared_manifest.workflow_run_id),
        manifest_id=prepared_manifest.manifest_id,
        execution_fingerprint=prepared_manifest.execution_fingerprint,
        resumed=resumed,
    )
