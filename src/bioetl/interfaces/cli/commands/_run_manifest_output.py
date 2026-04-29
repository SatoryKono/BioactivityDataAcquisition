"""Private text renderers for run-manifest CLI commands."""

from __future__ import annotations

import json

from bioetl.interfaces.cli.commands._run_manifest_output_support import (
    format_block,
    format_scalar,
    render_diagnostics_section,
    render_identity_graph_section,
    render_ledger_section,
    render_manifest_section,
    render_reproducibility_compact_section,
)


def _render_jsonish_block(value: object) -> list[str]:
    """Render nested data compactly for text mode without JSON path escaping noise."""
    rendered = json.dumps(value, indent=2, sort_keys=True, default=str)
    return rendered.replace("\\\\", "\\").splitlines()


def render_show_payload(payload: dict[str, object]) -> str:
    """Render one manifest inspection payload in human-readable form."""
    manifest = payload.get("manifest", {})
    ledger_entries = payload.get("ledger_entries", [])
    diagnostics = payload.get("diagnostics", {})
    identity_graph = payload.get("identity_graph", {})

    if not isinstance(ledger_entries, list):
        ledger_entries = []
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    if not isinstance(identity_graph, dict):
        identity_graph = {}

    if not isinstance(manifest, dict):
        return json.dumps(payload, indent=2, default=str)

    lines: list[str] = []
    lines.extend(render_manifest_section(manifest, json_renderer=_render_jsonish_block))

    if lines:
        lines.append("")
    lines.extend(render_ledger_section(ledger_entries))

    repro_lines = render_reproducibility_compact_section(
        diagnostics,
        json_renderer=_render_jsonish_block,
    )
    if lines and (repro_lines or (isinstance(ledger_entries, list) and ledger_entries)):
        lines.append("")
    lines.extend(repro_lines)

    if lines and repro_lines:
        lines.append("")
    lines.extend(
        render_diagnostics_section(diagnostics, json_renderer=_render_jsonish_block)
    )

    identity_graph_lines = render_identity_graph_section(
        identity_graph,
        json_renderer=_render_jsonish_block,
    )
    if lines and identity_graph_lines:
        lines.append("")
    lines.extend(identity_graph_lines)

    return "\n".join(lines)


def render_diff_payload(payload: dict[str, object]) -> str:
    """Render one manifest diff payload in human-readable form."""
    left_manifest_id = payload.get("left_manifest_id")
    right_manifest_id = payload.get("right_manifest_id")
    differences = payload.get("differences", [])
    lines: list[str] = [
        "Manifest Diff",
        f"  left_manifest_id: {format_scalar(left_manifest_id)}",
        f"  right_manifest_id: {format_scalar(right_manifest_id)}",
        f"  classification: {format_scalar(payload.get('classification'))}",
        f"  semantic_equivalent: {format_scalar(payload.get('semantic_equivalent'))}",
        f"  occurrence_only: {format_scalar(payload.get('occurrence_only'))}",
        f"  replay_relationship: {format_scalar(payload.get('replay_relationship'))}",
    ]
    for label in (
        "occurrence_difference_fields",
        "semantic_difference_fields",
        "noncanonical_difference_fields",
    ):
        value = payload.get(label)
        if value in (None, [], ()):
            continue
        rendered = format_block(value, json_renderer=_render_jsonish_block)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)
    if not isinstance(differences, list) or not differences:
        lines.append("  differences: 0")
        return "\n".join(lines)
    lines.append(f"  differences: {len(differences)}")
    for entry in differences:
        if not isinstance(entry, dict):
            lines.append("")
            lines.append(f"- {format_scalar(entry)}")
            continue
        lines.append("")
        lines.append(f"- field: {format_scalar(entry.get('field'))}")
        for side in ("left", "right"):
            rendered = format_block(
                entry.get(side), json_renderer=_render_jsonish_block
            )
            if len(rendered) == 1:
                lines.append(f"  {side}: {rendered[0]}")
                continue
            lines.append(f"  {side}:")
            lines.extend(f"    {line}" for line in rendered)
    return "\n".join(lines)


def render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "manifest" in payload:
        return render_show_payload(payload)
    if "differences" in payload:
        return render_diff_payload(payload)
    return json.dumps(payload, indent=2, default=str)
