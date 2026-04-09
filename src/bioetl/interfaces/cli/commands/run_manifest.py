"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "COMMANDS",
    "diff_command",
    "run_manifest",
    "show_command",
]


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_run_manifest_service as _impl,
    )

    return _impl()


def _format_scalar(value: object) -> str:
    """Format one scalar value for text-mode CLI output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_block(value: object) -> list[str]:
    """Format nested values as one or more human-readable text lines."""
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
    """Append a titled section to text output."""
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


def _render_manifest_section(manifest: dict[str, object]) -> list[str]:
    """Render manifest section."""
    lines: list[str] = []
    provenance = manifest.get("code_provenance", {})

    _append_section(
        lines,
        "Manifest",
        (
            ("manifest_id", manifest.get("manifest_id")),
            ("run_id", manifest.get("run_id")),
            ("pipeline_name", manifest.get("pipeline_name")),
            ("provider", manifest.get("provider")),
            ("entity", manifest.get("entity")),
            ("run_type", manifest.get("run_type")),
            ("created_at", manifest.get("created_at")),
            ("execution_fingerprint", manifest.get("execution_fingerprint")),
            ("schema_version", manifest.get("schema_version")),
        ),
    )

    if isinstance(provenance, dict):
        _append_section(
            lines,
            "Code Provenance",
            (
                ("pipeline_version", provenance.get("pipeline_version")),
                ("git_commit", provenance.get("git_commit")),
                ("config_hash", provenance.get("config_hash")),
            ),
        )

    _append_section(
        lines,
        "Execution Inputs",
        (
            ("launch_context", manifest.get("launch_context")),
            ("runtime_config", manifest.get("runtime_config")),
            ("resolved_config", manifest.get("resolved_config")),
            ("source_refs", manifest.get("source_refs")),
            ("planned_artifacts", manifest.get("planned_artifacts")),
        ),
    )

    return lines


def _render_ledger_section(ledger_entries: list[object]) -> list[str]:
    """Render ledger section."""
    lines: list[str] = []

    if isinstance(ledger_entries, list) and ledger_entries:
        lines.append("Ledger")
        lines.append(f"  entries: {len(ledger_entries)}")
        for entry in ledger_entries:
            if not isinstance(entry, dict):
                lines.append(f"  - {_format_scalar(entry)}")
                continue
            summary = f"{entry.get('occurred_at', '?')} {entry.get('event_type', '?')}"
            stage = entry.get("stage")
            status = entry.get("status")
            if stage is not None:
                summary += f" stage={stage}"
            if status is not None:
                summary += f" status={status}"
            lines.append(f"  - {summary}")
    else:
        _append_section(lines, "Ledger", (("entries", 0),))

    return lines


def _render_diagnostics_section(diagnostics: dict[str, object]) -> list[str]:
    """Render diagnostics section."""
    lines: list[str] = []

    if isinstance(diagnostics, dict):
        _append_section(
            lines,
            "Diagnostics",
            (
                ("latest_status", diagnostics.get("latest_status")),
                ("latest_event_type", diagnostics.get("latest_event_type")),
                ("total_events", diagnostics.get("total_events")),
                ("execution_fingerprint", diagnostics.get("execution_fingerprint")),
                ("config_hash", diagnostics.get("config_hash")),
                ("contract_ref", diagnostics.get("contract_ref")),
                ("contract_version", diagnostics.get("contract_version")),
                ("dq_policy_ref", diagnostics.get("dq_policy_ref")),
                ("rule_bundle_version", diagnostics.get("rule_bundle_version")),
                (
                    "effective_config_artifact_id",
                    diagnostics.get("effective_config_artifact_id"),
                ),
                (
                    "dq_contract_compatibility_hash",
                    diagnostics.get("dq_contract_compatibility_hash"),
                ),
                ("event_family_counts", diagnostics.get("event_family_counts")),
                ("event_type_counts", diagnostics.get("event_type_counts")),
                ("planned_artifact_count", diagnostics.get("planned_artifact_count")),
                (
                    "published_artifact_count",
                    diagnostics.get("published_artifact_count"),
                ),
                ("missing_artifact_links", diagnostics.get("missing_artifact_links")),
                ("lineage_fragment_ids", diagnostics.get("lineage_fragment_ids")),
                ("artifact_refs", diagnostics.get("artifact_refs")),
                (
                    "identity_graph_complete",
                    diagnostics.get("identity_graph_complete"),
                ),
                ("identity_graph", diagnostics.get("identity_graph")),
                ("dq_rule_ids", diagnostics.get("dq_rule_ids")),
                ("dq_dispositions", diagnostics.get("dq_dispositions")),
                ("dq_report_paths", diagnostics.get("dq_report_paths")),
                ("dq_violation_kinds", diagnostics.get("dq_violation_kinds")),
                (
                    "cross_validation_rule_ids",
                    diagnostics.get("cross_validation_rule_ids"),
                ),
                (
                    "cross_validation_config_paths",
                    diagnostics.get("cross_validation_config_paths"),
                ),
                (
                    "cross_validation_signal_present",
                    diagnostics.get("cross_validation_signal_present"),
                ),
                (
                    "correlation_anchor_gaps",
                    diagnostics.get("correlation_anchor_gaps"),
                ),
                ("alert_signals", diagnostics.get("alert_signals")),
                ("next_steps", diagnostics.get("next_steps")),
            ),
        )

    return lines


def _render_show_payload(payload: dict[str, object]) -> str:
    """Render one manifest inspection payload in human-readable form."""
    manifest = payload.get("manifest", {})
    ledger_entries = payload.get("ledger_entries", [])
    diagnostics = payload.get("diagnostics", {})

    if not isinstance(manifest, dict):
        return json.dumps(payload, indent=2, default=str)

    # Render all sections
    lines: list[str] = []
    lines.extend(_render_manifest_section(manifest))

    if lines:
        lines.append("")
    lines.extend(_render_ledger_section(ledger_entries))

    if lines and (isinstance(ledger_entries, list) and ledger_entries):
        lines.append("")
    lines.extend(_render_diagnostics_section(diagnostics))

    return "\n".join(lines)


def _render_diff_payload(payload: dict[str, object]) -> str:
    """Render one manifest diff payload in human-readable form."""
    left_manifest_id = payload.get("left_manifest_id")
    right_manifest_id = payload.get("right_manifest_id")
    differences = payload.get("differences", [])
    lines: list[str] = [
        "Manifest Diff",
        f"  left_manifest_id: {_format_scalar(left_manifest_id)}",
        f"  right_manifest_id: {_format_scalar(right_manifest_id)}",
    ]
    if not isinstance(differences, list) or not differences:
        lines.append("  differences: 0")
        return "\n".join(lines)
    lines.append(f"  differences: {len(differences)}")
    for entry in differences:
        if not isinstance(entry, dict):
            lines.append("")
            lines.append(f"- {_format_scalar(entry)}")
            continue
        lines.append("")
        lines.append(f"- field: {_format_scalar(entry.get('field'))}")
        for side in ("left", "right"):
            rendered = _format_block(entry.get(side))
            if len(rendered) == 1:
                lines.append(f"  {side}: {rendered[0]}")
                continue
            lines.append(f"  {side}:")
            lines.extend(f"    {line}" for line in rendered)
    return "\n".join(lines)


def _render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "manifest" in payload:
        return _render_show_payload(payload)
    if "differences" in payload:
        return _render_diff_payload(payload)
    return json.dumps(payload, indent=2, default=str)


@click.group()  # type: ignore[untyped-decorator]
def run_manifest() -> None:
    """Inspect control-plane run manifests and ledger history."""


@run_manifest.command("show")  # type: ignore[untyped-decorator]
@click.argument("identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_command(identifier: str, output_format: str) -> None:
    """Show one manifest by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


@run_manifest.command("diff")  # type: ignore[untyped-decorator]
@click.argument("left_identifier")  # type: ignore[untyped-decorator]
@click.argument("right_identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diff_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Diff two manifests resolved by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.diff(left_identifier, right_identifier)
    except ValueError as exc:
        echo_error("Run manifest diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


COMMANDS = (
    diff_command,
    show_command,
)
