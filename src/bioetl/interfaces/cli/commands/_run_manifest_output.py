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


def _render_cross_surface_replay_diff(payload: dict[str, object]) -> list[str]:
    """Render the replay-oriented cross-surface diff summary."""
    diff = payload.get("cross_surface_replay_diff")
    if not isinstance(diff, dict) or not diff:
        return []

    effective_config = diff.get("effective_config")
    checkpoint_anchors = diff.get("checkpoint_anchors")
    lineage = diff.get("lineage")
    if not isinstance(effective_config, dict):
        effective_config = {}
    if not isinstance(checkpoint_anchors, dict):
        checkpoint_anchors = {}
    if not isinstance(lineage, dict):
        lineage = {}

    lines = [
        "  cross_surface_replay_diff:",
        f"    verdict: {format_scalar(diff.get('verdict'))}",
        "    effective_config:",
        "      semantic_equivalent: "
        f"{format_scalar(effective_config.get('semantic_equivalent'))}",
        "    checkpoint_anchors:",
        f"      compatible: {format_scalar(checkpoint_anchors.get('compatible'))}",
    ]
    mismatched = checkpoint_anchors.get("mismatched_fields")
    if mismatched:
        lines.append("      mismatched_fields:")
        lines.extend(f"        {line}" for line in _render_jsonish_block(mismatched))
    lines.extend(
        [
            "    lineage:",
            "      planned_artifacts_match: "
            f"{format_scalar(lineage.get('planned_artifacts_match'))}",
        ]
    )
    return lines


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
    lines.extend(_render_cross_surface_replay_diff(payload))
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


def render_forensic_diff_payload(payload: dict[str, object]) -> str:
    """Render one cross-artifact forensic diff payload in human-readable form."""
    lines = [
        "Forensic Run Diff",
        f"  left_manifest_id: {format_scalar(payload.get('left_manifest_id'))}",
        f"  right_manifest_id: {format_scalar(payload.get('right_manifest_id'))}",
        f"  classification: {format_scalar(payload.get('classification'))}",
        f"  semantic_equivalent: {format_scalar(payload.get('semantic_equivalent'))}",
        f"  occurrence_only: {format_scalar(payload.get('occurrence_only'))}",
        f"  replay_relationship: {format_scalar(payload.get('replay_relationship'))}",
    ]
    lines.extend(_render_cross_surface_replay_diff(payload))
    for label in (
        "replay_capability",
        "checkpoint_compatibility",
        "artifact_completeness",
        "lineage_closure",
        "missing_evidence",
    ):
        rendered = format_block(payload.get(label), json_renderer=_render_jsonish_block)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)
    return "\n".join(lines)


def render_score_payload(payload: dict[str, object]) -> str:
    """Render one run-manifest score payload in human-readable text mode."""
    score = payload.get("reproducibility_audit_score")
    if not isinstance(score, dict):
        return json.dumps(payload, indent=2, default=str)

    boundary_verdict = score.get("supported_boundary_verdict")
    global_claim = score.get("global_reproducibility_claim")
    lines = [
        "Run Manifest Score",
        f"  identifier: {format_scalar(payload.get('identifier'))}",
        f"  manifest_id: {format_scalar(payload.get('manifest_id'))}",
        f"  run_id: {format_scalar(payload.get('run_id'))}",
        f"  run_scoped_score: {format_scalar(score.get('overall_score'))}",
        f"  score_scope: {format_scalar(score.get('score_scope'))}",
        f"  required_profile: {format_scalar(score.get('required_profile'))}",
        f"  thresholds_satisfied: {format_scalar(score.get('thresholds_satisfied'))}",
    ]
    if isinstance(boundary_verdict, dict):
        lines.extend(
            [
                "  supported_boundary_verdict:",
                f"    verdict: {format_scalar(boundary_verdict.get('verdict'))}",
                "    supported_boundary_satisfied: "
                f"{format_scalar(boundary_verdict.get('supported_boundary_satisfied'))}",
                f"    reason: {format_scalar(boundary_verdict.get('reason'))}",
                "    exact_replay_support_boundary: "
                f"{format_scalar(boundary_verdict.get('exact_replay_support_boundary'))}",
            ]
        )
    if isinstance(global_claim, dict):
        lines.extend(
            [
                "  global_reproducibility_claim:",
                f"    claimed: {format_scalar(global_claim.get('claimed'))}",
                f"    verdict: {format_scalar(global_claim.get('verdict'))}",
                f"    reason: {format_scalar(global_claim.get('reason'))}",
            ]
        )
    return "\n".join(lines)


def render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "manifest" in payload:
        return render_show_payload(payload)
    if "differences" in payload:
        return render_diff_payload(payload)
    if "manifest_diff" in payload and "forensic_diff" in payload:
        return render_forensic_diff_payload(payload)
    if "reproducibility_audit_score" in payload:
        return render_score_payload(payload)
    return json.dumps(payload, indent=2, default=str)
