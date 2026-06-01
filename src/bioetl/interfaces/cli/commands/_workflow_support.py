"""Shared workflow CLI support helpers."""

from __future__ import annotations

from dataclasses import replace

from bioetl.application.services.control_plane.workflow.inspection_service import (
    WorkflowInspectionResult,
)
from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
)
from bioetl.domain.workflow import (
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.interfaces.cli.formatters import echo_info

__all__ = [
    "apply_cli_overrides",
    "build_status_payload",
    "parse_only_steps",
    "render_run_result",
    "render_status_payload",
    "select_workflow_steps",
]


def parse_only_steps(raw_value: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated workflow step IDs from one CLI option."""
    if raw_value is None:
        return None
    parsed = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not parsed:
        raise ValueError("--only-steps must contain at least one step ID")
    return parsed


def select_workflow_steps(
    config: WorkflowConfig,
    only_steps: str | None,
) -> WorkflowConfig:
    """Filter workflow config to selected steps and required dependencies."""
    selected_step_ids = parse_only_steps(only_steps)
    if selected_step_ids is None:
        return config

    missing = [
        step_id for step_id in selected_step_ids if config.get_step(step_id) is None
    ]
    if missing:
        raise ValueError("Unknown workflow step IDs: " + ", ".join(sorted(missing)))

    required = set(selected_step_ids)
    pending = list(selected_step_ids)
    while pending:
        step_id = pending.pop()
        step = config.get_step(step_id)
        if step is None:
            continue
        for dependency in step.depends_on:
            if dependency not in required:
                required.add(dependency)
                pending.append(dependency)

    filtered_steps = tuple(step for step in config.steps if step.step_id in required)
    return replace(config, steps=filtered_steps)


def apply_cli_overrides(
    config: WorkflowConfig,
    *,
    dry_run: bool,
    run_type: str | None,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    log_level: str | None,
    ignore_yaml_filter: bool | None,
    skip_gold: bool | None,
    execution_context: str | None,
    use_cached_bronze: bool | None,
    cached_bronze_path: str | None,
    cached_bronze_date: str | None,
    exact_replay: bool | None,
    required_persistence_profile: str | None,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    enable_tracing: bool | None,
) -> WorkflowConfig:
    """Apply CLI overrides to workflow defaults and pipeline steps."""
    override = WorkflowRunOptionsConfig(
        dry_run=True if dry_run else None,
        run_type=run_type,
        start_offset=start_offset,
        limit=limit,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        vacuum_after_run=vacuum_after_run,
        vacuum_retention_days=vacuum_retention_days,
        log_level=log_level,
        ignore_yaml_filter=ignore_yaml_filter,
        skip_gold=skip_gold,
        execution_context=execution_context,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
        exact_replay=exact_replay,
        required_persistence_profile=required_persistence_profile,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        enable_tracing=enable_tracing,
    )
    if not override.to_mapping():
        return config

    updated_steps = []
    for step in config.steps:
        if isinstance(step, WorkflowStepConfig):
            updated_steps.append(
                replace(
                    step,
                    run_options=step.run_options.merged_with(override),
                )
            )
            continue
        updated_steps.append(step)

    return replace(
        config,
        defaults=config.defaults.merged_with(override),
        steps=tuple(updated_steps),
    )


def build_status_payload(
    config: WorkflowConfig,
    *,
    only_steps: str | None,
    inspection: WorkflowInspectionResult | None,
) -> dict[str, object]:
    """Build workflow status payload for text/json/yaml rendering."""
    steps = []
    for step in config.steps:
        base = {
            "step_id": step.step_id,
            "depends_on": list(step.depends_on),
        }
        if isinstance(step, WorkflowStepConfig):
            base.update(
                {
                    "kind": "pipeline",
                    "pipeline_name": step.pipeline_name,
                    "run_options": step.run_options.to_mapping(),
                }
            )
        else:
            base.update(
                {
                    "kind": "transform",
                    "transform_name": step.transform_name,
                    "config": step.config or {},
                }
            )
        steps.append(base)

    if inspection is not None:
        return {
            "workflow": config.name,
            "version": config.version,
            "selected_step_filter": list(parse_only_steps(only_steps) or ()),
            "topological_step_ids": list(config.topological_step_ids),
            "execution_history_available": True,
            "history_scope": "durable-workflow-control-plane",
            "workflow_run_id": inspection.workflow_run_id,
            "manifest_id": inspection.manifest_id,
            "execution_fingerprint": inspection.execution_fingerprint,
            "status": inspection.status,
            "repair_required": inspection.repair_required,
            "repair_hint": inspection.repair_hint,
            "ambiguous_step_ids": list(inspection.ambiguous_step_ids),
            "last_error_type": inspection.last_error_type,
            "last_error_message": inspection.last_error_message,
            "ledger_entry_count": inspection.ledger_entry_count,
            "steps": list(inspection.step_states),
            "note": (
                "Workflow status is backed by persisted workflow manifest, "
                "workflow ledger, and workflow execution state."
            ),
        }

    return {
        "workflow": config.name,
        "version": config.version,
        "selected_step_filter": list(parse_only_steps(only_steps) or ()),
        "topological_step_ids": list(config.topological_step_ids),
        "execution_history_available": False,
        "history_scope": "bounded-static-config",
        "note": (
            "No persisted workflow execution state was found. This status surface "
            "shows declarative step topology only."
        ),
        "steps": steps,
    }


def render_status_payload(payload: dict[str, object]) -> str:
    """Render workflow status payload as human-readable text."""
    workflow_name = str(payload["workflow"])
    version = str(payload["version"])
    topological = payload.get("topological_step_ids", [])
    steps = payload.get("steps", [])
    lines = [
        f"Workflow Status / {workflow_name}",
        f"version: {version}",
        "topological order: " + ", ".join(str(item) for item in topological),
    ]
    lines.extend(_render_history_lines(payload))
    lines.extend(["", "Steps:"])
    lines.extend(_render_status_steps(steps))
    lines.append("")
    lines.append(str(payload["note"]))
    return "\n".join(lines)


def _render_history_lines(payload: dict[str, object]) -> list[str]:
    """Render optional persisted workflow execution state."""
    if bool(payload.get("execution_history_available")):
        lines = [
            f"status: {payload['status']}",
            f"workflow_run_id: {payload['workflow_run_id']}",
            f"manifest_id: {payload['manifest_id']}",
            f"execution_fingerprint: {payload['execution_fingerprint']}",
            f"ledger_entries: {payload['ledger_entry_count']}",
        ]
        return lines + _render_repair_and_error_lines(payload)
    return ["history: unavailable"]


def _render_repair_and_error_lines(payload: dict[str, object]) -> list[str]:
    """Render optional repair hints and terminal workflow errors."""
    lines: list[str] = []
    if payload.get("repair_required"):
        lines.append("repair_required: yes")
    if payload.get("repair_hint"):
        lines.append(f"repair_hint: {payload['repair_hint']}")
    if payload.get("last_error_type") or payload.get("last_error_message"):
        lines.append(
            "last_error: "
            f"{payload.get('last_error_type') or 'Unknown'} / "
            f"{payload.get('last_error_message') or '-'}"
        )
    return lines


def _render_status_steps(steps: object) -> list[str]:
    """Render declarative workflow steps when the payload has a valid list."""
    if not isinstance(steps, list):
        return []
    rendered: list[str] = []
    for step in steps:
        if isinstance(step, dict):
            rendered.append(_render_status_step(step))
    return rendered


def _render_status_step(step: dict[str, object]) -> str:
    """Render one workflow status step."""
    depends_on = step.get("depends_on") or []
    depends_rendered = ", ".join(str(item) for item in depends_on) or "-"
    kind = str(step.get("kind", step.get("step_kind", "unknown")))
    if kind == "pipeline" and "pipeline_name" in step:
        return (
            f"- {step['step_id']} [{kind}] pipeline={step['pipeline_name']} "
            f"depends_on={depends_rendered}"
        )
    if kind == "transform" and "transform_name" in step:
        return (
            f"- {step['step_id']} [{kind}] transform={step['transform_name']} "
            f"depends_on={depends_rendered}"
        )
    summary = f"- {step['step_id']} [{kind}] -> {step.get('status', 'unknown')}"
    error_type = step.get("error_type")
    error_message = step.get("error_message")
    if error_type or error_message:
        summary += f" ({error_type or 'Error'}: {error_message or '-'})"
    return summary


def render_run_result(
    config: WorkflowConfig,
    result: WorkflowRunExecutionResult,
    *,
    dry_run: bool,
    only_steps: str | None,
    resume_last: bool,
) -> None:
    """Render final workflow execution result in human-readable CLI form."""
    echo_info(f"Workflow: {config.name}")
    echo_info(f"Status: {result.status}")
    echo_info(f"Dry-run: {'yes' if dry_run else 'no'}")
    echo_info(f"Resume-last: {'yes' if resume_last else 'no'}")
    if result.workflow_run_id is not None:
        echo_info(f"Workflow run ID: {result.workflow_run_id}")
    if result.manifest_id is not None:
        echo_info(f"Manifest ID: {result.manifest_id}")
    if result.execution_fingerprint is not None:
        echo_info(f"Execution fingerprint: {result.execution_fingerprint}")
    if result.resumed:
        echo_info("Execution mode: resumed")
    if only_steps:
        echo_info(f"Only steps: {only_steps}")
    echo_info("Steps:")
    for step in result.steps:
        summary = f"  - {step.step_id} [{step.step_kind}] -> {step.status}"
        if step.error_type is not None:
            summary += f" ({step.error_type}: {step.error_message})"
        payload = getattr(step, "payload", None)
        output = getattr(payload, "output", None)
        if (
            step.step_kind == "transform"
            and isinstance(output, dict)
            and output.get("dry_run") is True
            and output.get("would_mutate") is True
        ):
            summary += " (dry-run blocked destructive mutation)"
        echo_info(summary)
