"""Lineage inspection commands for BioETL CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_argument,
    typed_click_group,
    typed_click_option,
    typed_group_command,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )

__all__ = [
    "COMMANDS",
    "explain_command",
    "lineage",
    "show_fragment_command",
    "trace_command",
]

_NONE_BULLET = "  - none"


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage inspection service through composition on demand."""
    from bioetl.composition.control_plane_service_access import (
        get_lineage_service as _impl,
    )

    return _impl()


def _render_node_lines(nodes: list[object]) -> list[str]:
    """Render node payloads as compact human-readable bullet lines."""
    lines: list[str] = []
    for item in nodes:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        node_type = item.get("node_type", "?")
        node_id = item.get("node_id", "?")
        label = item.get("label")
        suffix = f" label={label}" if label not in (None, "") else ""
        lines.append(f"  - {node_type}: {node_id}{suffix}")
    return lines or [_NONE_BULLET]


def _render_relation_lines(relations: list[object]) -> list[str]:
    """Render trace relations as compact human-readable bullet lines."""
    lines: list[str] = []
    for item in relations:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        node = item.get("node", {})
        fragment_id = item.get("fragment_id", "?")
        stored_fragment_id = item.get("stored_fragment_id")
        edge_type = item.get("edge_type", "?")
        fragment_suffix = ""
        if stored_fragment_id not in (None, "", fragment_id):
            fragment_suffix = f" occurrence={stored_fragment_id}"
        if isinstance(node, dict):
            node_id = node.get("node_id", "?")
            label = node.get("label")
            suffix = f" label={label}" if label not in (None, "") else ""
            lines.append(
                f"  - {edge_type} via {fragment_id}{fragment_suffix}: {node_id}{suffix}"
            )
            continue
        lines.append(f"  - {edge_type} via {fragment_id}{fragment_suffix}: {node}")
    return lines or [_NONE_BULLET]


def _render_fragment_payload(payload: dict[str, object]) -> str:
    """Render one fragment inspection payload in human-readable form."""
    fragment = payload.get("fragment", {})
    if not isinstance(fragment, dict):
        return json.dumps(payload, indent=2, default=str)
    lines = [
        "Lineage Fragment",
        f"  fragment_id: {fragment.get('fragment_id')}",
        f"  stored_fragment_id: {fragment.get('stored_fragment_id')}",
        f"  run_id: {fragment.get('run_id')}",
        f"  manifest_id: {fragment.get('manifest_id')}",
        f"  created_at: {fragment.get('created_at')}",
        f"  nodes: {len(fragment.get('nodes', [])) if isinstance(fragment.get('nodes'), list) else 0}",
        f"  edges: {len(fragment.get('edges', [])) if isinstance(fragment.get('edges'), list) else 0}",
        "",
        "Nodes",
    ]
    nodes = fragment.get("nodes")
    if isinstance(nodes, list):
        lines.extend(_render_node_lines(nodes))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_trace_payload(payload: dict[str, object]) -> str:
    """Render one trace payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    stored_fragment_ids = payload.get("stored_fragment_ids")
    stored_fragment_count = (
        len(stored_fragment_ids) if isinstance(stored_fragment_ids, list) else 0
    )
    lines = [
        "Lineage Trace",
        f"  dataset_ref: {payload.get('dataset_ref')}",
        f"  fragments: {fragment_count}",
        f"  stored_fragments: {stored_fragment_count}",
        "",
        "Upstream",
    ]
    upstream = payload.get("upstream")
    if isinstance(upstream, list):
        lines.extend(_render_relation_lines(upstream))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Downstream"])
    downstream = payload.get("downstream")
    if isinstance(downstream, list):
        lines.extend(_render_relation_lines(downstream))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_explain_payload(payload: dict[str, object]) -> str:
    """Render one run explanation payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    stored_fragment_ids = payload.get("stored_fragment_ids")
    stored_fragment_count = (
        len(stored_fragment_ids) if isinstance(stored_fragment_ids, list) else 0
    )
    lines = [
        "Lineage Run",
        f"  identifier: {payload.get('identifier')}",
        f"  run_id: {payload.get('run_id')}",
        f"  manifest_id: {payload.get('manifest_id')}",
        f"  fragments: {fragment_count}",
        f"  stored_fragments: {stored_fragment_count}",
        "",
        "Produced Datasets",
    ]
    produced_datasets = payload.get("produced_datasets")
    if isinstance(produced_datasets, list):
        lines.extend(_render_node_lines(produced_datasets))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Produced Bronze Batches"])
    produced_bronze_batches = payload.get("produced_bronze_batches")
    if isinstance(produced_bronze_batches, list):
        lines.extend(_render_node_lines(produced_bronze_batches))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Transforms"])
    transforms = payload.get("transforms")
    if isinstance(transforms, list):
        lines.extend(_render_node_lines(transforms))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Source Systems"])
    source_systems = payload.get("source_systems")
    if isinstance(source_systems, list):
        lines.extend(_render_node_lines(source_systems))
    else:
        lines.append(_NONE_BULLET)
    lines.extend(["", "Source Requests"])
    source_requests = payload.get("source_requests")
    if isinstance(source_requests, list):
        lines.extend(_render_node_lines(source_requests))
    else:
        lines.append(_NONE_BULLET)
    return "\n".join(lines)


def _render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "fragment" in payload:
        return _render_fragment_payload(payload)
    if "dataset_ref" in payload:
        return _render_trace_payload(payload)
    if "identifier" in payload:
        return _render_explain_payload(payload)
    return json.dumps(payload, indent=2, default=str)


def _resolve_explain_identifier(
    *,
    run_id: str | None,
    manifest_id: str | None,
) -> str | None:
    """Resolve exactly one explain identifier from CLI options."""
    if bool(run_id) == bool(manifest_id):
        return None
    return run_id if run_id is not None else manifest_id


@typed_click_group()
def lineage() -> None:
    """Inspect persisted lineage fragments and run traceability."""


@typed_group_command(lineage, "show-fragment")
@typed_click_argument("fragment_id")
@typed_click_option(
    "--semantic",
    is_flag=True,
    help="Use diagnostic semantic fragment-id lookup instead of occurrence id.",
)
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_fragment_command(
    fragment_id: str,
    semantic: bool,
    output_format: str,
) -> None:
    """Show one lineage fragment by FRAGMENT_ID."""
    service = get_lineage_service()
    try:
        result = service.show_fragment(fragment_id, semantic=semantic)
    except ValueError as exc:
        echo_error("Lineage fragment not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


@typed_group_command(lineage, "trace")
@typed_click_option(
    "--dataset-ref",
    required=True,
    help="Canonical dataset/node ref, e.g. silver:chembl.activity@12",
)
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def trace_command(dataset_ref: str, output_format: str) -> None:
    """Trace immediate upstream and downstream lineage for one dataset ref."""
    service = get_lineage_service()
    try:
        result = service.trace(dataset_ref)
    except ValueError as exc:
        echo_error("Lineage trace not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


@typed_group_command(lineage, "explain")
@typed_click_option("--run-id", default=None, help="Resolve lineage by RUN_ID")
@typed_click_option(
    "--manifest-id", default=None, help="Resolve lineage by MANIFEST_ID"
)
@typed_click_option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def explain_command(
    run_id: str | None,
    manifest_id: str | None,
    output_format: str,
) -> None:
    """Explain the lineage graph attached to one run or manifest."""
    identifier = _resolve_explain_identifier(run_id=run_id, manifest_id=manifest_id)
    if identifier is None:
        echo_error(
            "Lineage explain failed",
            "Provide exactly one of --run-id or --manifest-id",
        )
        raise SystemExit(1)

    service = get_lineage_service()
    try:
        result = service.explain_run(identifier)
    except ValueError as exc:
        echo_error("Lineage run explanation not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=_render_text_payload,
    )


COMMANDS = (
    explain_command,
    show_fragment_command,
    trace_command,
)
