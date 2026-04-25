"""Checkpoint management commands for BioETL CLI.

Implements checkpoint listing and management commands.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_checkpoint, echo_error, echo_info

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )

__all__ = [
    "COMMANDS",
    "checkpoint",
    "checkpoint_audit_run",
    "checkpoint_inspect",
    "checkpoint_list",
]

_NONE_ENTRY_LINE = "  - none"


@click.group()
def checkpoint() -> None:
    """Manage checkpoints."""


def get_checkpoint_manager(pipeline: str) -> CheckpointManagerService:
    """Load the checkpoint manager through composition on demand."""
    from bioetl.composition.resources_api import get_checkpoint_manager as _impl

    impl = cast("Callable[[str], CheckpointManagerService]", _impl)
    return impl(pipeline)


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load observability workflows through the canonical public interface."""
    from bioetl.interfaces.observability import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


def _render_audit_entry_lines(entries: list[object]) -> list[str]:
    """Render audit entries as compact operator-facing lines."""
    lines: list[str] = []
    for item in entries:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        line = (
            "  - "
            f"{item.get('timestamp', '?')} "
            f"{item.get('layer', '?')}/{item.get('table_name', '?')} "
            f"{item.get('operation', '?')} "
            f"records={item.get('records_count', '?')}"
        )
        lines.append(line)
    return lines or [_NONE_ENTRY_LINE]


def _resolve_replay_view(
    run_manifest: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """Return manifest metadata plus the preferred replay diagnostics view."""
    manifest = run_manifest.get("manifest", {})
    diagnostics = run_manifest.get("diagnostics", {})
    identity_graph = run_manifest.get("identity_graph", {})
    replay_view = (
        identity_graph
        if isinstance(identity_graph, dict) and identity_graph
        else diagnostics
    )
    return (
        manifest if isinstance(manifest, dict) else None,
        replay_view if isinstance(replay_view, dict) else None,
    )


def _extract_persistence_profile_details(
    replay_view: dict[str, object],
) -> tuple[object | None, object | None, object | None, object | None]:
    """Return the operator-facing persistence profile details from replay view."""
    persistence_profile = replay_view.get("persistence_profile")
    if not isinstance(persistence_profile, dict):
        return None, None, None, None
    return (
        persistence_profile.get("attained_profile"),
        persistence_profile.get("composite_resume_reconstructability"),
        persistence_profile.get("replay_ready_missing_requirements"),
        persistence_profile.get("forensic_grade_missing_requirements"),
    )


def _render_audit_run_manifest_lines(
    run_manifest: dict[str, object],
) -> list[str]:
    """Render manifest and replay diagnostics lines for audit-run output."""
    manifest, replay_view = _resolve_replay_view(run_manifest)
    lines: list[str] = []
    if manifest is not None:
        lines.extend(
            [
                f"  manifest_id: {manifest.get('manifest_id')}",
                f"  pipeline_name: {manifest.get('pipeline_name')}",
            ]
        )
    if replay_view is None:
        return lines

    (
        attained_profile,
        composite_resume_reconstructability,
        replay_ready_missing_requirements,
        forensic_grade_missing_requirements,
    ) = _extract_persistence_profile_details(replay_view)
    lines.extend(
        [
            f"  replay_capability: {replay_view.get('replay_capability')}",
            f"  requested_exact_replay: {replay_view.get('requested_exact_replay')}",
            f"  exact_replay_support_boundary: {replay_view.get('exact_replay_support_boundary')}",
            f"  replay_capability_reason: {replay_view.get('replay_capability_reason')}",
            f"  exact_replay_blockers: {replay_view.get('exact_replay_blockers')}",
            f"  input_snapshot_ids: {replay_view.get('input_snapshot_ids')}",
            f"  input_snapshot_identity_fingerprint: {replay_view.get('input_snapshot_identity_fingerprint')}",
            f"  persistence_profile: {attained_profile}",
            f"  replay_ready_missing_requirements: {replay_ready_missing_requirements}",
            f"  forensic_grade_missing_requirements: {forensic_grade_missing_requirements}",
            f"  composite_resume_reconstructability: {composite_resume_reconstructability}",
            f"  alert_signals: {replay_view.get('alert_signals')}",
            f"  next_steps: {replay_view.get('next_steps')}",
        ]
    )
    return lines


def _render_audit_run_payload(payload: dict[str, object]) -> str:
    """Render one audit-run inspection payload in human-readable text."""
    audit = payload.get("audit", {})
    run_manifest = payload.get("run_manifest")
    entries = audit.get("entries", []) if isinstance(audit, dict) else []
    lines = [
        "Audit Run Diagnostics",
        f"  run_id: {payload.get('run_id')}",
        f"  audit_entries: {len(entries) if isinstance(entries, list) else 0}",
    ]
    if isinstance(run_manifest, dict):
        lines.extend(_render_audit_run_manifest_lines(run_manifest))
    lines.extend(["", "Audit Entries"])
    if isinstance(entries, list):
        lines.extend(_render_audit_entry_lines(entries))
    else:
        lines.append(_NONE_ENTRY_LINE)
    return "\n".join(lines)


def _render_checkpoint_workflow_payload(payload: dict[str, object]) -> str:
    """Render one checkpoint workflow payload in human-readable text."""
    checkpoint = payload.get("checkpoint")
    audit = payload.get("audit", {})
    run_manifest = payload.get("run_manifest")
    entries = audit.get("entries", []) if isinstance(audit, dict) else []
    lines = [
        "Checkpoint Workflow Diagnostics",
        f"  pipeline_name: {payload.get('pipeline_name')}",
    ]
    if isinstance(checkpoint, dict):
        lines.extend(
            [
                f"  checkpoint_run_id: {checkpoint.get('run_id')}",
                f"  checkpoint_metadata_keys: "
                f"{len(checkpoint.get('metadata', {})) if isinstance(checkpoint.get('metadata'), dict) else 0}",
            ]
        )
    else:
        lines.append("  checkpoint: none")
    if isinstance(run_manifest, dict):
        manifest = run_manifest.get("manifest", {})
        if isinstance(manifest, dict):
            lines.extend(
                [
                    f"  manifest_id: {manifest.get('manifest_id')}",
                    f"  manifest_run_id: {manifest.get('run_id')}",
                ]
            )
    lines.extend(
        [
            f"  audit_entries: {len(entries) if isinstance(entries, list) else 0}",
            "",
            "Audit Entries",
        ]
    )
    if isinstance(entries, list):
        lines.extend(_render_audit_entry_lines(entries))
    else:
        lines.append(_NONE_ENTRY_LINE)
    return "\n".join(lines)


def _render_checkpoint_payload(payload: dict[str, object]) -> str:
    """Render checkpoint CLI inspection payload in text mode."""
    if "run_id" in payload and "audit" in payload and "pipeline_name" not in payload:
        return _render_audit_run_payload(payload)
    if "pipeline_name" in payload and "audit" in payload:
        return _render_checkpoint_workflow_payload(payload)
    return json.dumps(payload, indent=2, default=str)


@checkpoint.command("list")
@click.option("--pipeline", required=True, help="Pipeline name")
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints.

    Args:
        pipeline: Pipeline.
    """
    echo_info(f"Listing checkpoints for {pipeline}...")

    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            echo_checkpoint(cp)

    asyncio.run(_list())


@checkpoint.command("audit-run")
@click.option("--run-id", required=True, help="Pipeline RUN_ID to inspect")
@click.option("--limit", default=100, show_default=True, help="Maximum audit entries")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def checkpoint_audit_run(run_id: str, limit: int, output_format: str) -> None:
    """Inspect one pipeline run across audit and run-manifest observability surfaces."""
    workflow_service = get_observability_workflow_service()

    async def _inspect() -> None:
        try:
            result = await workflow_service.inspect_audit_run(run_id, limit=limit)
        except ValueError as exc:
            echo_error("Audit run diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@checkpoint.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--run-id", default=None, help="Optional RUN_ID override")
@click.option(
    "--audit-limit",
    default=100,
    show_default=True,
    help="Maximum audit entries",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def checkpoint_inspect(
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Inspect checkpoint state with correlated audit and run-manifest context."""
    workflow_service = get_observability_workflow_service()

    async def _inspect() -> None:
        try:
            result = await workflow_service.inspect_checkpoint_workflow(
                pipeline,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        except ValueError as exc:
            echo_error("Checkpoint diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


# Hint for tooling: explicit reference to command function.
COMMANDS = (checkpoint_list, checkpoint_audit_run, checkpoint_inspect)
