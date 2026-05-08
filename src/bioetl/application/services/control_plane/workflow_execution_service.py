"""Workflow execution orchestration with manifest, ledger, state, and locking."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import uuid4

from bioetl.application.services.control_plane.workflow_ledger_service import (
    WorkflowLedgerService,
)
from bioetl.application.services.control_plane.workflow_manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.application.services.control_plane.workflow_manifest_service import (
    WorkflowManifestService,
)
from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowRunnerService,
    WorkflowTransformDestructiveCommit,
    WorkflowStepExecutionResult,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.control_plane import (
    WorkflowExecutionState,
    WorkflowManifest,
    WorkflowStepState,
)
from bioetl.domain.ports import (
    LockPort,
    WorkflowExecutionStatePort,
    WorkflowLedgerPort,
)
from bioetl.domain.types import RunID
from bioetl.domain.workflow import TransformStepConfig, WorkflowConfig

__all__ = ["WorkflowExecutionService"]


@dataclass(slots=True)
class WorkflowExecutionService:
    """Orchestrate workflow execution around durable control-plane artifacts."""

    workflow_runner: WorkflowRunnerService
    manifest_service: WorkflowManifestService
    workflow_ledger_port: WorkflowLedgerPort
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
    ) -> WorkflowRunExecutionResult:
        """Execute a workflow with durable manifest, ledger, state, and lock."""
        resolved_launch_context = dict(launch_context or {})
        resolved_launch_context["resume_last"] = resume_last
        resolved_launch_context["force_steps"] = list(force_steps)
        resolved_launch_context["repair_steps"] = list(repair_steps)

        (
            manifest,
            state,
            completed_step_ids,
            completed_transform_fingerprints,
            resumed,
        ) = self._prepare_execution(
            config=config,
            launch_context=resolved_launch_context,
            resume_last=resume_last,
            force_steps=force_steps,
            repair_steps=repair_steps,
        )
        ledger = WorkflowLedgerService(
            ledger_port=self.workflow_ledger_port,
            manifest_id=manifest.manifest_id,
            workflow_run_id=manifest.workflow_run_id,
            workflow_name=manifest.workflow_name,
        )
        lock_key = f"workflow:{config.name}"
        token = await self.workflow_lock_port.acquire(
            lock_key,
            manifest.workflow_run_id,
            wait=False,
            exclusive=True,
        )
        if token is None:
            raise RuntimeError(
                f"Workflow '{config.name}' is already running inside the current local runtime boundary"
            )

        try:
            if not resumed:
                ledger.record_manifest_created(manifest)
            if repair_steps:
                ledger.record_repair_requested(step_ids=repair_steps)
            if force_steps:
                ledger.record_force_requested(step_ids=force_steps)
            started_entry = ledger.record_workflow_started(resumed=resumed)
            state = replace(
                state,
                status="running",
                updated_at=started_entry.occurred_at,
                last_event_id=started_entry.entry_id,
                repair_required=False,
                repair_hint=None,
                ambiguous_step_ids=tuple(
                    step_id
                    for step_id in state.ambiguous_step_ids
                    if step_id not in set(repair_steps)
                ),
            )
            self.workflow_state_port.save(state)

            def on_step_started(
                step: object,
                *,
                fingerprint: str | None = None,
            ) -> None:
                nonlocal state
                step_kind = (
                    "transform" if isinstance(step, TransformStepConfig) else "pipeline"
                )
                entry = ledger.record_step_started(
                    step_id=step.step_id,
                    step_kind=step_kind,
                    details=(
                        {"fingerprint": fingerprint}
                        if fingerprint is not None
                        else None
                    ),
                )
                state = _record_step_state(
                    state,
                    WorkflowStepState(
                        step_id=step.step_id,
                        step_kind=step_kind,
                        status="running",
                        fingerprint=fingerprint,
                    ),
                    updated_at=entry.occurred_at,
                    last_event_id=entry.entry_id,
                )
                self.workflow_state_port.save(state)

            def on_step_completed(result: WorkflowStepExecutionResult) -> None:
                nonlocal state
                fingerprint = _resolve_result_fingerprint(result)
                message = result.error_message
                entry = ledger.record_step_completed(
                    step_id=result.step_id,
                    step_kind=result.step_kind,
                    status=result.status,
                    message=message,
                    error_type=result.error_type,
                    details=(
                        {"fingerprint": fingerprint}
                        if fingerprint is not None
                        else None
                    ),
                )
                if result.error_type == "AlreadyCompletedOnResume":
                    state = replace(
                        state,
                        updated_at=entry.occurred_at,
                        last_event_id=entry.entry_id,
                    )
                else:
                    state = _record_step_state(
                        state,
                        WorkflowStepState(
                            step_id=result.step_id,
                            step_kind=result.step_kind,
                            status=result.status,
                            fingerprint=fingerprint,
                            error_type=result.error_type,
                            error_message=result.error_message,
                        ),
                        updated_at=entry.occurred_at,
                        last_event_id=entry.entry_id,
                    )
                    if (
                        result.step_kind == "transform"
                        and result.status == "success"
                        and fingerprint is not None
                    ):
                        updated_fingerprints = dict(
                            state.completed_transform_fingerprints
                        )
                        updated_fingerprints[result.step_id] = fingerprint
                        state = replace(
                            state,
                            completed_transform_fingerprints=updated_fingerprints,
                        )
                    ambiguous_step_ids = tuple(
                        step_id
                        for step_id in state.ambiguous_step_ids
                        if step_id != result.step_id
                    )
                    state = replace(
                        state,
                        repair_required=bool(ambiguous_step_ids),
                        repair_hint=(
                            None if not ambiguous_step_ids else state.repair_hint
                        ),
                        ambiguous_step_ids=ambiguous_step_ids,
                    )
                self.workflow_state_port.save(state)

            def on_transform_commit(commit: WorkflowTransformDestructiveCommit) -> None:
                nonlocal state
                entry = ledger.record_step_commit_pending_confirmation(
                    step_id=commit.step_id,
                    step_kind="transform",
                    details=commit.details,
                )
                current_step = _find_step_state(state, commit.step_id)
                state = _record_step_state(
                    state,
                    WorkflowStepState(
                        step_id=commit.step_id,
                        step_kind="transform",
                        status=(
                            "running" if current_step is None else current_step.status
                        ),
                        fingerprint=commit.fingerprint,
                        destructive=True,
                        commit_pending_confirmation=True,
                        mutation_details=commit.details,
                    ),
                    updated_at=entry.occurred_at,
                    last_event_id=entry.entry_id,
                )
                ambiguous_step_ids = tuple(
                    dict.fromkeys((*state.ambiguous_step_ids, commit.step_id))
                )
                state = replace(
                    state,
                    repair_required=True,
                    repair_hint=(
                        "A destructive workflow transform committed before terminal "
                        "confirmation. Resume requires explicit --repair-steps or "
                        "--force-steps for the ambiguous step."
                    ),
                    ambiguous_step_ids=ambiguous_step_ids,
                )
                self.workflow_state_port.save(state)

            result = await self.workflow_runner.run_workflow(
                config,
                completed_step_ids=completed_step_ids,
                completed_transform_fingerprints=completed_transform_fingerprints,
                step_started_callback=on_step_started,
                step_completed_callback=on_step_completed,
                transform_commit_callback=on_transform_commit,
            )

            completed_at = self.now_factory()
            summary = _build_result_summary(result)
            if result.status == "success":
                entry = ledger.record_workflow_finished(details=summary)
                state = replace(
                    state,
                    status="success",
                    updated_at=entry.occurred_at,
                    completed_at=completed_at,
                    last_event_id=entry.entry_id,
                    last_error_type=None,
                    last_error_message=None,
                )
            else:
                failed_step = _find_failed_step(result)
                entry = ledger.record_workflow_failed(
                    message=(
                        failed_step.error_message
                        if failed_step is not None and failed_step.error_message
                        else "Workflow execution failed"
                    ),
                    error_type=(
                        None if failed_step is None else failed_step.error_type
                    ),
                    details=summary,
                )
                state = replace(
                    state,
                    status="failed",
                    updated_at=entry.occurred_at,
                    completed_at=completed_at,
                    last_event_id=entry.entry_id,
                    last_error_type=(
                        None if failed_step is None else failed_step.error_type
                    ),
                    last_error_message=(
                        None if failed_step is None else failed_step.error_message
                    ),
                )
            self.workflow_state_port.save(state)
            return replace(
                result,
                workflow_run_id=str(manifest.workflow_run_id),
                manifest_id=manifest.manifest_id,
                execution_fingerprint=manifest.execution_fingerprint,
                resumed=resumed,
            )
        finally:
            await self.workflow_lock_port.release(
                lock_key,
                manifest.workflow_run_id,
                exclusive=True,
            )

    def _prepare_execution(
        self,
        *,
        config: WorkflowConfig,
        launch_context: dict[str, object],
        resume_last: bool,
        force_steps: tuple[str, ...],
        repair_steps: tuple[str, ...],
    ) -> tuple[
        WorkflowManifest,
        WorkflowExecutionState,
        frozenset[str],
        dict[str, str],
        bool,
    ]:
        request = WorkflowManifestCreateSpec(
            workflow_run_id=self.run_id_factory(),
            config=config,
            launch_context=launch_context,
        )
        current_fingerprint = self.manifest_service.compute_execution_fingerprint(
            request
        )
        if not resume_last:
            manifest = self.manifest_service.create_manifest(request)
            state = _build_initial_state(manifest)
            self.workflow_state_port.save(state)
            return manifest, state, frozenset(), {}, False

        latest_state = self.workflow_state_port.get_latest(config.name)
        if latest_state is None:
            raise RuntimeError(
                f"Workflow '{config.name}' has no persisted execution state for --resume-last"
            )
        if latest_state.execution_fingerprint != current_fingerprint:
            raise RuntimeError(
                "Workflow configuration changed since the last execution; "
                "--resume-last requires the same execution fingerprint"
            )
        if latest_state.status == "success":
            raise RuntimeError(
                f"Workflow '{config.name}' already completed successfully; nothing to resume"
            )
        if latest_state.repair_required and not (repair_steps or force_steps):
            raise RuntimeError(
                latest_state.repair_hint
                or "Workflow resume requires explicit --repair-steps or --force-steps"
            )
        manifest = self.manifest_service.manifest_port.get(latest_state.manifest_id)
        if manifest is None:
            raise RuntimeError(
                "Workflow resume failed because the persisted manifest could not be loaded"
            )
        normalized_state = latest_state
        if latest_state.status == "running":
            normalized_state = replace(
                latest_state,
                status="incomplete",
                updated_at=self.now_factory(),
            )
            self.workflow_state_port.save(normalized_state)
        skipped_step_ids = {
            step.step_id
            for step in normalized_state.steps
            if step.status == "success"
            and step.step_id not in set(force_steps)
            and step.step_id not in set(repair_steps)
        }
        completed_transform_fingerprints = {
            step_id: fingerprint
            for step_id, fingerprint in normalized_state.completed_transform_fingerprints.items()
            if step_id not in set(force_steps) and step_id not in set(repair_steps)
        }
        return (
            manifest,
            normalized_state,
            frozenset(skipped_step_ids),
            completed_transform_fingerprints,
            True,
        )


def _build_initial_state(manifest: WorkflowManifest) -> WorkflowExecutionState:
    now = manifest.created_at
    steps = tuple(
        WorkflowStepState(
            step_id=step.step_id,
            step_kind=step.kind,
            status="pending",
        )
        for step in manifest.steps
    )
    return WorkflowExecutionState(
        workflow_run_id=manifest.workflow_run_id,
        manifest_id=manifest.manifest_id,
        workflow_name=manifest.workflow_name,
        execution_fingerprint=manifest.execution_fingerprint,
        status="created",
        started_at=now,
        updated_at=now,
        completed_at=None,
        selected_step_ids=manifest.selected_step_ids,
        steps=steps,
        completed_transform_fingerprints={},
    )


def _record_step_state(
    state: WorkflowExecutionState,
    step_state: WorkflowStepState,
    *,
    updated_at: datetime,
    last_event_id: str,
) -> WorkflowExecutionState:
    updated_steps = []
    replaced_existing = False
    for current_step in state.steps:
        if current_step.step_id == step_state.step_id:
            updated_steps.append(step_state)
            replaced_existing = True
            continue
        updated_steps.append(current_step)
    if not replaced_existing:
        updated_steps.append(step_state)
    return replace(
        state,
        steps=tuple(updated_steps),
        updated_at=updated_at,
        last_event_id=last_event_id,
        last_error_type=step_state.error_type,
        last_error_message=step_state.error_message,
    )


def _resolve_result_fingerprint(result: WorkflowStepExecutionResult) -> str | None:
    payload = result.payload
    fingerprint = getattr(payload, "fingerprint", None)
    if fingerprint is not None:
        return str(fingerprint)
    if isinstance(payload, dict):
        dict_fingerprint = payload.get("fingerprint")
        if dict_fingerprint is not None:
            return str(dict_fingerprint)
    return None


def _find_step_state(
    state: WorkflowExecutionState,
    step_id: str,
) -> WorkflowStepState | None:
    for step in state.steps:
        if step.step_id == step_id:
            return step
    return None


def _build_result_summary(result: WorkflowRunExecutionResult) -> dict[str, object]:
    counts = {"success": 0, "failed": 0, "skipped": 0}
    for step in result.steps:
        if step.status in counts:
            counts[step.status] += 1
    return {"status": result.status, "step_counts": counts}


def _find_failed_step(
    result: WorkflowRunExecutionResult,
) -> WorkflowStepExecutionResult | None:
    for step in result.steps:
        if step.status == "failed":
            return step
    return None
