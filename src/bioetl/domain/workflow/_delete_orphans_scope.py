"""Scope delete_orphans away from independently bounded extracts."""

from __future__ import annotations

from dataclasses import replace

from bioetl.domain.workflow.config import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStep,
    WorkflowStepConfig,
)

__all__ = [
    "mark_delete_orphans_current_run_scope",
    "reject_delete_orphans_after_limited_extracts",
]


def _delete_orphans_transform(step: WorkflowStep) -> TransformStepConfig | None:
    """Return the step when it is a delete_orphans FK reconciliation."""
    if not isinstance(step, TransformStepConfig):
        return None
    if step.transform_name != "reconcile_foreign_keys":
        return None
    action = None if step.config is None else step.config.get("action")
    if action != "delete_orphans":
        return None
    return step


def _record_limited_upstream_dep(
    dep_id: str,
    *,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
    seen: set[str],
    stack: list[str],
    limited: list[str],
) -> None:
    """Walk one upstream dependency and record limited pipeline steps."""
    if dep_id in seen:
        return
    seen.add(dep_id)
    dep = steps_by_id.get(dep_id)
    if dep is None:
        return
    stack.extend(reversed(dep.depends_on))
    if not isinstance(dep, WorkflowStepConfig):
        return
    merged = config.defaults.merged_with(dep.run_options)
    if merged.limit is not None:
        limited.append(dep_id)


def _limited_upstream_pipeline_ids(
    start_id: str,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
) -> list[str]:
    """Return upstream pipeline step ids that carry run_options.limit."""
    limited: list[str] = []
    seen: set[str] = set()
    stack = list(reversed(steps_by_id[start_id].depends_on))
    while stack:
        _record_limited_upstream_dep(
            stack.pop(),
            config=config,
            steps_by_id=steps_by_id,
            seen=seen,
            stack=stack,
            limited=limited,
        )
    return limited


def _scope_delete_orphans_step(
    step: WorkflowStep,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
) -> tuple[WorkflowStep, bool]:
    """Scope one delete_orphans step to the current run when needed."""
    transform = _delete_orphans_transform(step)
    if transform is None:
        return step, False
    if not _limited_upstream_pipeline_ids(transform.step_id, config, steps_by_id):
        return step, False
    scoped = dict(transform.config or {})
    scoped["source_scope"] = "current_run"
    return replace(transform, config=scoped), True


def mark_delete_orphans_current_run_scope(config: WorkflowConfig) -> WorkflowConfig:
    """Scope delete_orphans to the current run when an extract is limited.

    CLI ``--limit`` is allowed together with ``delete_orphans``. Mutations then
    apply only to source rows from this workflow run, so independently bounded
    extracts cannot delete historical Gold as false-positive orphans.
    """
    updated_steps: list[WorkflowStep] = []
    changed = False
    steps_by_id = {item.step_id: item for item in config.steps}
    for step in config.steps:
        scoped_step, step_changed = _scope_delete_orphans_step(
            step, config, steps_by_id
        )
        updated_steps.append(scoped_step)
        if step_changed:
            changed = True
    if not changed:
        return config
    scoped_config: WorkflowConfig = replace(config, steps=tuple(updated_steps))
    return scoped_config


def reject_delete_orphans_after_limited_extracts(config: WorkflowConfig) -> None:
    """Reject committed YAML that bakes delete_orphans onto limited extracts.

    Independently bounded extracts make Gold FK orphans false positives.
    Walks the full upstream DAG so an intermediary transform cannot hide a
    limited producer. CLI ``--limit`` does not use this reject; it scopes
    mutations to the current run instead.
    """
    steps_by_id = {step.step_id: step for step in config.steps}
    for step in config.steps:
        transform = _delete_orphans_transform(step)
        if transform is None:
            continue
        limited = _limited_upstream_pipeline_ids(transform.step_id, config, steps_by_id)
        if limited:
            raise ValueError(
                "reconcile_foreign_keys action=delete_orphans cannot depend on "
                "pipeline steps with run_options.limit "
                f"({', '.join(limited)}); independently bounded extracts "
                "make Gold FK orphans false positives"
            )
