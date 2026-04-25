"""Contract migration planner command for BioETL CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    CLI_ENTRYPOINT_TYPED_ERRORS,
)
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    handle_cli_failure as handle_cli_execution_failure,
)
from bioetl.interfaces.cli.commands.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services import ContractMigrationService
    from collections.abc import Callable

__all__ = [
    "get_contract_migration_service",
    "plan_command",
]

_NONE_LINE = "  none"


def get_contract_migration_service() -> ContractMigrationService:
    """Load the contract migration service through composition on demand."""
    from bioetl.composition.maintenance_api import (
        get_contract_migration_service as _impl,
    )

    service_factory: Callable[[], ContractMigrationService] = _impl
    return service_factory()


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_block(value: object) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    if isinstance(value, list):
        if not value:
            return ["[]"]
        return json.dumps(value, indent=2, sort_keys=True, default=str).splitlines()
    return [_format_scalar(value)]


def _append_section(
    lines: list[str],
    title: str,
    items: Iterable[tuple[str, object]],
) -> None:
    filtered = [(label, value) for label, value in items if value not in (None, [], {})]
    if not filtered:
        return
    if lines:
        lines.append("")
    lines.append(title)
    for label, value in filtered:
        rendered = _format_block(value)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)


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
            lines.append(f"  - {_format_scalar(entry)}")
            continue
        line = (
            "  - "
            f"{_format_scalar(entry.get('from_version'))} -> "
            f"{_format_scalar(entry.get('to_version'))}"
        )
        if entry.get("migration_guide") is not None:
            line += f" (guide: {_format_scalar(entry.get('migration_guide'))})"
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
            lines.append(f"  - {_format_scalar(action)}")
            continue
        title = _format_scalar(action.get("title"))
        code = _format_scalar(action.get("code"))
        description = _format_scalar(action.get("description"))
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
        lines.append(f"  - {_format_scalar(note)}")


def _render_plan_payload(payload: dict[str, object]) -> str:
    lines: list[str] = []
    _append_section(
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
    )
    _append_transitions(lines, payload.get("transitions"))
    _append_required_actions(lines, payload.get("required_actions"))
    _append_notes(lines, payload.get("notes"))
    return "\n".join(lines)


def _handle_plan_failure(
    exc: BaseException, *, pipeline: str, reason_code: str
) -> None:
    handle_cli_execution_failure(
        exc,
        reason_code=reason_code,
        subject_key="pipeline",
        subject_value=pipeline,
        domain_error_title="Contract migration planning failed with domain error",
        unexpected_error_title="Unexpected error during maintenance plan",
        interrupted_message="Maintenance plan interrupted by user (Ctrl+C)",
        default_exit_code=ExitCode.FAIL,
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
    try:
        plan = service.plan_pipeline(pipeline)
        emit_inspection_payload(
            plan.to_payload(),
            output_format,
            text_renderer=_render_plan_payload,
        )
    except BioETLError as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_DOMAIN_ERROR",
        )
    except KeyboardInterrupt as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_SIGINT",
        )
    except CLI_ENTRYPOINT_TYPED_ERRORS as exc:
        _handle_plan_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_MAINTENANCE_PLAN_UNEXPECTED_ERROR",
        )
