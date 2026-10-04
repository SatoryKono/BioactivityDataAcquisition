"""Scope delete_orphans away from independently bounded extracts."""

from __future__ import annotations

from collections.abc import Mapping
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
    scoped = dict(_transform_options(transform))
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


def _transform_options(transform: TransformStepConfig) -> Mapping[str, object]:
    """Expose optional transform configuration with an empty default."""
    return transform.config or {}


def _step_definitions(config: WorkflowConfig) -> dict[str, WorkflowStep]:
    """Index the workflow for consistent upstream traversal."""
    return {step.step_id: step for step in config.steps}


def _ancestors(step: WorkflowStep, definitions: dict[str, WorkflowStep]) -> set[str]:
    """Collect each upstream step once, including through transform nodes."""
    ancestors: set[str] = set()
    pending = list(step.depends_on)
    while pending:
        identity = pending.pop()
        if identity not in ancestors:
            ancestors.add(identity)
            pending.extend(definitions[identity].depends_on)
    return ancestors


def _cohort_matches(
    producer: WorkflowStepConfig, options: Mapping[str, object]
) -> bool:
    """Match either orientation of the explicitly bound reference relation."""
    cohort = producer.reference_cohort
    if cohort is None:
        return False
    relation = (
        producer.pipeline_name.replace("_", ".", 1),
        cohort.table,
        cohort.column,
    )
    return relation in (
        (
            options.get("reference_table"),
            options.get("source_table"),
            options.get("source_key"),
        ),
        (
            options.get("source_table"),
            options.get("reference_table"),
            options.get("reference_key"),
        ),
    )


def _has_bound_reference_cohort(
    transform: TransformStepConfig, config: WorkflowConfig
) -> bool:
    """Permit bounded verification only for an explicitly linked ancestor."""
    options = _transform_options(transform)
    if options.get("require_closed_cohort") is not True:
        return False
    ancestors = _ancestors(transform, _step_definitions(config))
    return any(
        _cohort_matches(producer, options)
        for producer in config.pipeline_steps
        if producer.step_id in ancestors
    )


def _reject_limited_transform(
    transform: TransformStepConfig,
    config: WorkflowConfig,
    definitions: dict[str, WorkflowStep],
) -> None:
    """Require complete references unless bounded selection evidence is linked."""
    mode = (_transform_options(transform)).get(
        "reconciliation_mode",
        config.defaults.reconciliation_mode or "complete-reference",
    )
    if mode == "selected-snapshot":
        return
    limited = _limited_upstream_pipeline_ids(transform.step_id, config, definitions)
    if limited and not _has_bound_reference_cohort(transform, config):
        raise ValueError(
            "reconcile_foreign_keys action=delete_orphans cannot depend on "
            "pipeline steps with run_options.limit "
            f"({', '.join(limited)}); independently bounded extracts "
            "make Gold FK orphans false positives"
        )


def reject_delete_orphans_after_limited_extracts(config: WorkflowConfig) -> None:
    """Reject destructive reconciliation after independently bounded extracts."""
    definitions = _step_definitions(config)
    for step in config.steps:
        transform = _delete_orphans_transform(step)
        if transform is not None:
            _reject_limited_transform(transform, config, definitions)


def _apply_transform_mode(
    transform: TransformStepConfig, config: WorkflowConfig, mode: str | None
) -> tuple[WorkflowStep, bool]:
    """Bind the effective mode and indicate whether producer capture is needed."""
    from bioetl.domain.workflow.foreign_key_reconciliation import (
        require_reconciliation_mode,
    )

    values = dict(_transform_options(transform))
    effective = require_reconciliation_mode(
        mode
        or config.defaults.reconciliation_mode
        or str(values.get("reconciliation_mode", "complete-reference"))
    )
    if effective == "selected-snapshot":
        values.update(reconciliation_mode=effective, source_scope="current_run")
        return replace(transform, config=values), True
    if mode is not None:
        values["reconciliation_mode"] = effective
        return replace(transform, config=values), False
    return transform, False


def _capture_producer(step: WorkflowStep, producers: set[str]) -> WorkflowStep:
    """Mark selected producer steps without modifying unrelated run options."""
    if isinstance(step, WorkflowStepConfig) and step.step_id in producers:
        return replace(
            step,
            run_options=replace(
                step.run_options, reconciliation_mode="selected-snapshot"
            ),
        )
    return step


def apply_reconciliation_mode(
    config: WorkflowConfig, mode: str | None = None
) -> WorkflowConfig:
    """Bind effective mode and bounded source scope into transform fingerprints."""
    steps: list[WorkflowStep] = []
    producers: set[str] = set()
    definitions = _step_definitions(config)
    for step in config.steps:
        transform = _delete_orphans_transform(step)
        if transform is None:
            steps.append(step)
            continue
        updated, selected = _apply_transform_mode(transform, config, mode)
        steps.append(updated)
        if selected:
            producers.update(_ancestors(transform, definitions))
    return replace(
        config, steps=tuple(_capture_producer(step, producers) for step in steps)
    )
