"""Declarative workflow CLI commands."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import TYPE_CHECKING

import click

from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow_inspection_service import (
        WorkflowInspectionResult,
        WorkflowInspectionService,
    )
    from bioetl.application.services.workflow_runner_service import (
        WorkflowRunExecutionResult,
    )
    from bioetl.composition.registry_api import PipelineRegistry

__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "load_workflow_config",
    "workflow",
]


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load one declarative workflow config through composition seams."""
    from bioetl.composition.services_api import load_workflow_config as _impl

    return _impl(name)


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowExecutionService:
    """Resolve workflow execution orchestration through composition seams."""
    from bioetl.composition.services_api import (
        get_workflow_execution_service as _impl,
    )

    return _impl(registry=registry)


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Resolve workflow inspection through composition seams."""
    from bioetl.composition.services_api import (
        get_workflow_inspection_service as _impl,
    )

    return _impl()


@click.group()
def workflow() -> None:
    """Run and inspect declarative workflows."""


@workflow.command("run")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Enable dry-run for pipeline steps")
@click.option(
    "--only-steps",
    help="Comma-separated subset of step IDs to execute with required dependencies",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    help="Override workflow pipeline run_type for this execution",
)
@click.option(
    "--resume-last",
    is_flag=True,
    help="Resume the latest incomplete or failed execution for this workflow",
)
@click.option(
    "--force-steps",
    help="Comma-separated step IDs to force even when resume would normally skip them",
)
@click.option(
    "--repair-steps",
    help="Comma-separated step IDs to explicitly repair before resume proceeds",
)
@click.pass_obj
def run_workflow_command(
    registry: PipelineRegistry | None,
    name: str,
    dry_run: bool,
    only_steps: str | None,
    run_type: str | None,
    resume_last: bool,
    force_steps: str | None,
    repair_steps: str | None,
) -> None:
    """Execute one declarative workflow config sequentially."""
    try:
        config = load_workflow_config(name)
        config = _select_workflow_steps(config, only_steps)
        config = _apply_cli_overrides(
            config,
            dry_run=dry_run,
            run_type=run_type,
        )
    except (FileNotFoundError, ValueError) as exc:
        echo_error("Workflow configuration error", str(exc))
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR) from exc

    parsed_force_steps = _parse_only_steps(force_steps) or ()
    parsed_repair_steps = _parse_only_steps(repair_steps) or ()
    result = asyncio.run(
        get_workflow_execution_service(registry=registry).run_workflow(
            config,
            launch_context={"only_steps": list(_parse_only_steps(only_steps) or ())},
            resume_last=resume_last,
            force_steps=parsed_force_steps,
            repair_steps=parsed_repair_steps,
        )
    )
    _render_run_result(
        config,
        result,
        dry_run=dry_run,
        only_steps=only_steps,
        resume_last=resume_last,
    )
    if result.status == "failed":
        raise click.exceptions.Exit(ExitCode.PIPELINE_ERROR)


@workflow.command("status")
@click.argument("name")
@click.option(
    "--only-steps",
    help="Comma-separated subset of step IDs to inspect with required dependencies",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option("--run-id", help="Inspect one specific workflow run ID")
def workflow_status_command(
    name: str,
    only_steps: str | None,
    output_format: str,
    run_id: str | None,
) -> None:
    """Show workflow status with durable execution details when available."""
    try:
        config = load_workflow_config(name)
        config = _select_workflow_steps(config, only_steps)
    except (FileNotFoundError, ValueError) as exc:
        echo_error("Workflow configuration error", str(exc))
        raise click.exceptions.Exit(ExitCode.CONFIG_ERROR) from exc

    inspection = (
        get_workflow_inspection_service().inspect_run_id(run_id)
        if run_id is not None
        else get_workflow_inspection_service().inspect_latest(config.name)
    )
    payload = _build_status_payload(
        config,
        only_steps=only_steps,
        inspection=inspection,
    )
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=_render_status_payload,
    )


def _parse_only_steps(raw_value: str | None) -> tuple[str, ...] | None:
    if raw_value is None:
        return None
    parsed = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not parsed:
        raise ValueError("--only-steps must contain at least one step ID")
    return parsed


def _select_workflow_steps(
    config: WorkflowConfig,
    only_steps: str | None,
) -> WorkflowConfig:
    selected_step_ids = _parse_only_steps(only_steps)
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


def _apply_cli_overrides(
    config: WorkflowConfig,
    *,
    dry_run: bool,
    run_type: str | None,
) -> WorkflowConfig:
    override = WorkflowRunOptionsConfig(
        dry_run=True if dry_run else None,
        run_type=run_type,
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


def _build_status_payload(
    config: WorkflowConfig,
    *,
    only_steps: str | None,
    inspection: WorkflowInspectionResult | None,
) -> dict[str, object]:
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
            "selected_step_filter": list(_parse_only_steps(only_steps) or ()),
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
        "selected_step_filter": list(_parse_only_steps(only_steps) or ()),
        "topological_step_ids": list(config.topological_step_ids),
        "execution_history_available": False,
        "history_scope": "bounded-static-config",
        "note": (
            "No persisted workflow execution state was found. This status surface "
            "shows declarative step topology only."
        ),
        "steps": steps,
    }


def _render_status_payload(payload: dict[str, object]) -> str:
    workflow_name = str(payload["workflow"])
    version = str(payload["version"])
    topological = payload.get("topological_step_ids", [])
    steps = payload.get("steps", [])
    lines = [
        f"Workflow Status / {workflow_name}",
        f"version: {version}",
        "topological order: " + ", ".join(str(item) for item in topological),
    ]
    if bool(payload.get("execution_history_available")):
        lines.extend(
            [
                f"status: {payload['status']}",
                f"workflow_run_id: {payload['workflow_run_id']}",
                f"manifest_id: {payload['manifest_id']}",
                f"execution_fingerprint: {payload['execution_fingerprint']}",
                f"ledger_entries: {payload['ledger_entry_count']}",
            ]
        )
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
    else:
        lines.append("history: unavailable")
    lines.extend(["", "Steps:"])
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            depends_on = step.get("depends_on") or []
            depends_rendered = ", ".join(str(item) for item in depends_on) or "-"
            kind = str(step.get("kind", step.get("step_kind", "unknown")))
            if kind == "pipeline" and "pipeline_name" in step:
                lines.append(
                    f"- {step['step_id']} [{kind}] pipeline={step['pipeline_name']} "
                    f"depends_on={depends_rendered}"
                )
            elif kind == "transform" and "transform_name" in step:
                lines.append(
                    f"- {step['step_id']} [{kind}] transform={step['transform_name']} "
                    f"depends_on={depends_rendered}"
                )
            else:
                summary = f"- {step['step_id']} [{kind}] -> {step.get('status', 'unknown')}"
                error_type = step.get("error_type")
                error_message = step.get("error_message")
                if error_type or error_message:
                    summary += f" ({error_type or 'Error'}: {error_message or '-'})"
                lines.append(summary)
    lines.append("")
    lines.append(str(payload["note"]))
    return "\n".join(lines)


def _render_run_result(
    config: WorkflowConfig,
    result: WorkflowRunExecutionResult,
    *,
    dry_run: bool,
    only_steps: str | None,
    resume_last: bool,
) -> None:
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
        echo_info(summary)
