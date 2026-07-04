"""Contract migration planner command for the maintenance CLI domain."""

from __future__ import annotations

import json

import click

from bioetl.interfaces.cli.commands.domains.maintenance.service_access import (
    get_contract_migration_service,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CliBoundaryExecutionPolicy,
    run_sync_with_cli_failure_policy,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output_support import (
    append_section,
    format_scalar,
)

__all__ = ["get_contract_migration_service", "plan_command"]

_NONE_LINE = "  none"


def _render_json_block(value: object) -> list[str]:
    return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()


def _append_transitions(lines: list[str], transitions: object) -> None:
    if not isinstance(transitions, list):
        return
    if lines:
        lines.append("")
    lines.append("Transitions")
    if not transitions:
        lines.append(_NONE_LINE)
        return
    for entry in transitions:
        if not isinstance(entry, dict):
            lines.append(f"  - {format_scalar(entry)}")
            continue
        line = (
            "  - "
            f"{format_scalar(entry.get('from_version'))} -> "
            f"{format_scalar(entry.get('to_version'))}"
        )
        if entry.get("migration_guide") is not None:
            line += f" (guide: {format_scalar(entry.get('migration_guide'))})"
        if entry.get("affects_hash") is True:
            line += " [affects_hash]"
        lines.append(line)


def _append_required_actions(lines: list[str], required_actions: object) -> None:
    if not isinstance(required_actions, list):
        return
    if lines:
        lines.append("")
    lines.append("Required Actions")
    if not required_actions:
        lines.append(_NONE_LINE)
        return
    for action in required_actions:
        if not isinstance(action, dict):
            lines.append(f"  - {format_scalar(action)}")
            continue
        title = format_scalar(action.get("title"))
        code = format_scalar(action.get("code"))
        description = format_scalar(action.get("description"))
        lines.append(f"  - {title} [{code}]")
        lines.append(f"    {description}")


def _append_notes(lines: list[str], notes: object) -> None:
    if not isinstance(notes, list):
        return
    if lines:
        lines.append("")
    lines.append("Notes")
    if not notes:
        lines.append(_NONE_LINE)
        return
    for note in notes:
        lines.append(f"  - {format_scalar(note)}")


def _render_plan_payload(payload: dict[str, object]) -> str:
    lines: list[str] = []
    append_section(
        lines,
        "Contract Migration Plan",
        (
            ("pipeline_name", payload.get("pipeline_name")),
            ("provider", payload.get("provider")),
            ("entity_type", payload.get("entity_type")),
            ("contract_ref", payload.get("contract_ref")),
            ("active_version", payload.get("active_version")),
            ("rollout_mode", payload.get("rollout_mode")),
            ("affects_hash", payload.get("affects_hash")),
            ("read_order", payload.get("read_order")),
            ("write_versions", payload.get("write_versions")),
            ("shadow_versions", payload.get("shadow_versions")),
            ("supported_versions", payload.get("supported_versions")),
        ),
        json_renderer=_render_json_block,
    )
    _append_transitions(lines, payload.get("transitions"))
    _append_required_actions(lines, payload.get("required_actions"))
    _append_notes(lines, payload.get("notes"))
    return "\n".join(lines)


def _plan_policy(pipeline: str) -> CliBoundaryExecutionPolicy:
    """Build the shared CLI boundary policy for the contract planner."""
    return CliBoundaryExecutionPolicy(
        reason_prefix="CLI_MAINTENANCE_PLAN",
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title="Contract migration planning failed with domain error",
        unexpected_error_title="Unexpected error during maintenance plan",
        interrupted_message="Maintenance plan interrupted by user (Ctrl+C)",
    )


@click.command("plan")
@click.argument("pipeline")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    show_default=True,
    help="Output format for the planner payload.",
)
def plan_command(pipeline: str, output_format: str) -> None:
    """Plan contract migration actions for a pipeline.

    PIPELINE: Registered pipeline name (for example, ``chembl_activity``).
    """
    service = get_contract_migration_service()

    def _run() -> None:
        plan = service.plan_pipeline(pipeline)
        emit_inspection_payload(
            plan.to_payload(),
            output_format,
            text_renderer=_render_plan_payload,
        )

    run_sync_with_cli_failure_policy(_run, policy=_plan_policy(pipeline))
