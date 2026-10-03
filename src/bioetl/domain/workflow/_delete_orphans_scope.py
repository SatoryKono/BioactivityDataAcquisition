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


def _require_workflow_config(value: object) -> WorkflowConfig:
    """Return a concrete workflow config after validating replacement output."""
    if not isinstance(value, WorkflowConfig):
        raise TypeError("dataclass replacement did not preserve WorkflowConfig")
    return value


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

    This compatibility helper only narrows source scope. It does not establish
    reference completeness; callers must still reject limited extracts before
    executing destructive reconciliation.
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
    return _require_workflow_config(replace(config, steps=tuple(updated_steps)))


def _has_bound_reference_cohort(
    transform: TransformStepConfig, config: WorkflowConfig
) -> bool:
    """Permit bounded verification only for an explicitly linked selection."""
    options = transform.config or {}
    if options.get("require_closed_cohort") is not True:
        return False
    source_table, reference_table = (
        options.get("source_table"),
        options.get("reference_table"),
    )
    expected_links = (
        (reference_table, source_table, options.get("source_key")),
        (source_table, reference_table, options.get("reference_key")),
    )
    return any(
        _producer_cohort_link(producer) in expected_links
        for producer in config.pipeline_steps
    )


def reject_delete_orphans_after_limited_extracts(config: WorkflowConfig) -> None:
    """Reject effective configuration with delete_orphans on limited extracts.

    Independently bounded extracts make Gold FK orphans false positives.
    Walks the full upstream DAG so an intermediary transform cannot hide a
    limited producer. Apply this after CLI overrides as well as YAML loading.
    """
    steps_by_id = {step.step_id: step for step in config.steps}
    for step in config.steps:
        transform = _delete_orphans_transform(step)
        if transform is None:
            continue
        _reject_limited_delete_orphans(transform, config, steps_by_id)


def _producer_cohort_link(producer: WorkflowStepConfig) -> tuple[str, str, str] | None:
    """Describe a selected cohort link without duplicating the orientation checks."""
    cohort = producer.reference_cohort
    if cohort is None:
        return None
    return producer.pipeline_name.replace("_", ".", 1), cohort.table, cohort.column


def _reject_limited_delete_orphans(
    transform: TransformStepConfig,
    config: WorkflowConfig,
    steps_by_id: dict[str, WorkflowStep],
) -> None:
    """Reject one destructive transform unless its limited cohort is bound."""
    limited = _limited_upstream_pipeline_ids(transform.step_id, config, steps_by_id)
    if not limited:
        return
    if _has_bound_reference_cohort(transform, config):
        return
    raise ValueError(
        "reconcile_foreign_keys action=delete_orphans cannot depend on "
        "pipeline steps with run_options.limit "
        f"({', '.join(limited)}); independently bounded extracts "
        "make Gold FK orphans false positives"
    )
