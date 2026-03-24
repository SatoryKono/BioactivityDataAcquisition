"""Lineage inspection commands for BioETL CLI."""

from __future__ import annotations

import json

import click
import yaml

from bioetl.interfaces.cli.formatters import echo_error, echo_info

__all__ = [
    "COMMANDS",
    "explain_command",
    "lineage",
    "show_fragment_command",
    "trace_command",
]


def get_lineage_service() -> object:
    """Load the lineage inspection service through composition on demand."""
    from bioetl.composition.services_api import get_lineage_service as _impl

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
    return lines or ["  - none"]


def _render_relation_lines(relations: list[object]) -> list[str]:
    """Render trace relations as compact human-readable bullet lines."""
    lines: list[str] = []
    for item in relations:
        if not isinstance(item, dict):
            lines.append(f"  - {item}")
            continue
        node = item.get("node", {})
        fragment_id = item.get("fragment_id", "?")
        edge_type = item.get("edge_type", "?")
        if isinstance(node, dict):
            node_id = node.get("node_id", "?")
            label = node.get("label")
            suffix = f" label={label}" if label not in (None, "") else ""
            lines.append(
                f"  - {edge_type} via {fragment_id}: {node_id}{suffix}"
            )
            continue
        lines.append(f"  - {edge_type} via {fragment_id}: {node}")
    return lines or ["  - none"]


def _render_fragment_payload(payload: dict[str, object]) -> str:
    """Render one fragment inspection payload in human-readable form."""
    fragment = payload.get("fragment", {})
    if not isinstance(fragment, dict):
        return json.dumps(payload, indent=2, default=str)
    lines = [
        "Lineage Fragment",
        f"  fragment_id: {fragment.get('fragment_id')}",
        f"  run_id: {fragment.get('run_id')}",
        f"  manifest_id: {fragment.get('manifest_id')}",
        f"  created_at: {fragment.get('created_at')}",
        f"  nodes: {len(fragment.get('nodes', [])) if isinstance(fragment.get('nodes'), list) else 0}",
        f"  edges: {len(fragment.get('edges', [])) if isinstance(fragment.get('edges'), list) else 0}",
        "",
        "Nodes",
    ]
    if isinstance(fragment.get("nodes"), list):
        lines.extend(_render_node_lines(fragment["nodes"]))
    else:
        lines.append("  - none")
    return "\n".join(lines)


def _render_trace_payload(payload: dict[str, object]) -> str:
    """Render one trace payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    lines = [
        "Lineage Trace",
        f"  dataset_ref: {payload.get('dataset_ref')}",
        f"  fragments: {fragment_count}",
        "",
        "Upstream",
    ]
    if isinstance(payload.get("upstream"), list):
        lines.extend(_render_relation_lines(payload["upstream"]))
    else:
        lines.append("  - none")
    lines.extend(["", "Downstream"])
    if isinstance(payload.get("downstream"), list):
        lines.extend(_render_relation_lines(payload["downstream"]))
    else:
        lines.append("  - none")
    return "\n".join(lines)


def _render_explain_payload(payload: dict[str, object]) -> str:
    """Render one run explanation payload in human-readable form."""
    fragment_ids = payload.get("fragment_ids")
    fragment_count = len(fragment_ids) if isinstance(fragment_ids, list) else 0
    lines = [
        "Lineage Run",
        f"  identifier: {payload.get('identifier')}",
        f"  run_id: {payload.get('run_id')}",
        f"  manifest_id: {payload.get('manifest_id')}",
        f"  fragments: {fragment_count}",
        "",
        "Produced Datasets",
    ]
    if isinstance(payload.get("produced_datasets"), list):
        lines.extend(_render_node_lines(payload["produced_datasets"]))
    else:
        lines.append("  - none")
    lines.extend(["", "Produced Bronze Batches"])
    if isinstance(payload.get("produced_bronze_batches"), list):
        lines.extend(_render_node_lines(payload["produced_bronze_batches"]))
    else:
        lines.append("  - none")
    lines.extend(["", "Transforms"])
    if isinstance(payload.get("transforms"), list):
        lines.extend(_render_node_lines(payload["transforms"]))
    else:
        lines.append("  - none")
    lines.extend(["", "Source Systems"])
    if isinstance(payload.get("source_systems"), list):
        lines.extend(_render_node_lines(payload["source_systems"]))
    else:
        lines.append("  - none")
    lines.extend(["", "Source Requests"])
    if isinstance(payload.get("source_requests"), list):
        lines.extend(_render_node_lines(payload["source_requests"]))
    else:
        lines.append("  - none")
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


@click.group()
def lineage() -> None:
    """Inspect persisted lineage fragments and run traceability."""


@lineage.command("show-fragment")
@click.argument("fragment_id")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_fragment_command(fragment_id: str, output_format: str) -> None:
    """Show one lineage fragment by FRAGMENT_ID."""
    service = get_lineage_service()
    try:
        result = service.show_fragment(fragment_id)
    except ValueError as exc:
        echo_error("Lineage fragment not found", str(exc))
        return
    _emit_payload(result.to_dict(), output_format)


@lineage.command("trace")
@click.option(
    "--dataset-ref",
    required=True,
    help="Canonical dataset/node ref, e.g. silver:chembl.activity@12",
)
@click.option(
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
    _emit_payload(result.to_dict(), output_format)


@lineage.command("explain")
@click.option("--run-id", default=None, help="Resolve lineage by RUN_ID")
@click.option("--manifest-id", default=None, help="Resolve lineage by MANIFEST_ID")
@click.option(
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
        return

    service = get_lineage_service()
    try:
        result = service.explain_run(identifier)
    except ValueError as exc:
        echo_error("Lineage run explanation not found", str(exc))
        return
    _emit_payload(result.to_dict(), output_format)


COMMANDS = (
    explain_command,
    show_fragment_command,
    trace_command,
)
