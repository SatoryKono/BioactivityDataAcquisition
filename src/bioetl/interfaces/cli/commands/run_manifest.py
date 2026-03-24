"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click
import yaml

from bioetl.interfaces.cli.formatters import echo_error, echo_info

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
    from bioetl.composition.services_api import get_run_manifest_service as _impl

    return _impl()


def _emit_payload(payload: dict[str, object], output_format: str) -> None:
    """Serialize CLI payload to the requested output format."""
    if output_format == "json":
        echo_info(json.dumps(payload, indent=2, default=str))
        return
    if output_format == "yaml":
        echo_info(yaml.dump(payload, default_flow_style=False, sort_keys=False))
        return
    echo_info(_render_text_payload(payload))


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


def _render_show_payload(payload: dict[str, object]) -> str:
    """Render one manifest inspection payload in human-readable form."""
    manifest = payload.get("manifest", {})
    ledger_entries = payload.get("ledger_entries", [])
    if not isinstance(manifest, dict):
        return json.dumps(payload, indent=2, default=str)
    provenance = manifest.get("code_provenance", {})
    lines: list[str] = []
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
    if isinstance(ledger_entries, list) and ledger_entries:
        if lines:
            lines.append("")
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


@click.group()
def run_manifest() -> None:
    """Inspect control-plane run manifests and ledger history."""


@run_manifest.command("show")
@click.argument("identifier")
@click.option(
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
    _emit_payload(result.to_dict(), output_format)


@run_manifest.command("diff")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
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
    _emit_payload(result.to_dict(), output_format)


COMMANDS = (
    diff_command,
    show_command,
)
