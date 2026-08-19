"""Scope and reject delete_orphans against limited upstream extracts."""

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


def _as_delete_orphans_transform(step: WorkflowStep) -> TransformStepConfig | None:
    if not isinstance(step, TransformStepConfig):
        return None
    if step.transform_name != "reconcile_foreign_keys":
        return None
    action = None if step.config is None else step.config.get("action")
    if action != "delete_orphans":
        return None
    return step


def _step_has_extract_limit(step: WorkflowStep, config: WorkflowConfig) -> bool:
    if not isinstance(step, WorkflowStepConfig):
        return False
    return config.defaults.merged_with(step.run_options).limit is not None


def _limited_upstream_pipeline_ids(
    start_id: str,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
) -> list[str]:
    limited: list[str] = []
    seen: set[str] = set()
    stack = list(reversed(steps_by_id[start_id].depends_on))
    while stack:
        dep_id = stack.pop()
        if dep_id in seen:
            continue
        seen.add(dep_id)
        dep = steps_by_id.get(dep_id)
        if dep is None:
            continue
        stack.extend(reversed(dep.depends_on))
        if _step_has_extract_limit(dep, config):
            limited.append(dep_id)
    return limited


def _scope_delete_orphans_step(
    step: WorkflowStep,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
) -> tuple[WorkflowStep, bool]:
    delete_orphans = _as_delete_orphans_transform(step)
    if delete_orphans is None:
        return step, False
    if not _limited_upstream_pipeline_ids(delete_orphans.step_id, config, steps_by_id):
        return step, False
    scoped = dict(delete_orphans.config or {})
    scoped["source_scope"] = "current_run"
    return replace(delete_orphans, config=scoped), True


def mark_delete_orphans_current_run_scope(config: WorkflowConfig) -> WorkflowConfig:
    """Scope delete_orphans to the current run when an extract is limited."""
    steps_by_id = {item.step_id: item for item in config.steps}
    updated_steps: list[WorkflowStep] = []
    changed = False
    for step in config.steps:
        scoped, did_change = _scope_delete_orphans_step(step, config, steps_by_id)
        updated_steps.append(scoped)
        changed = changed or did_change
    if not changed:
        return config
    return replace(config, steps=tuple(updated_steps))


def reject_delete_orphans_after_limited_extracts(config: WorkflowConfig) -> None:
    """Reject committed YAML that bakes delete_orphans onto limited extracts.

    Independently bounded extracts make Gold FK orphans false positives.
    Walks the full upstream DAG so an intermediary transform cannot hide a
    limited producer. CLI ``--limit`` does not use this reject; it scopes
    mutations to the current run instead.
    """
    steps_by_id = {step.step_id: step for step in config.steps}
    for step in config.steps:
        delete_orphans = _as_delete_orphans_transform(step)
        if delete_orphans is None:
            continue
        limited = _limited_upstream_pipeline_ids(
            delete_orphans.step_id, config, steps_by_id
        )
        if not limited:
            continue
        raise ValueError(
            "reconcile_foreign_keys action=delete_orphans cannot depend on "
            "pipeline steps with run_options.limit "
            f"({', '.join(limited)}); independently bounded extracts "
            "make Gold FK orphans false positives"
        )
