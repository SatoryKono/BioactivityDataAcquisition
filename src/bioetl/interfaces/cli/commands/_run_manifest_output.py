"""Private text renderers for run-manifest CLI commands."""

from __future__ import annotations

import json
from collections.abc import Iterable


def _format_scalar(value: object) -> str:
    """Format one scalar value for text-mode CLI output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render_jsonish_block(value: object) -> list[str]:
    """Render nested data compactly for text mode without JSON path escaping noise."""
    rendered = json.dumps(value, indent=2, sort_keys=True, default=str)
    return rendered.replace("\\\\", "\\").splitlines()


def _format_block(value: object) -> list[str]:
    """Format nested values as one or more human-readable text lines."""
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        return _render_jsonish_block(value)
    if isinstance(value, list):
        if not value:
            return ["[]"]
        if all(not isinstance(item, (dict, list)) for item in value):
            return [_format_scalar(item) for item in value]
        return _render_jsonish_block(value)
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
            ("replay_of_run_id", manifest.get("replay_of_run_id")),
            ("replay_of_manifest_id", manifest.get("replay_of_manifest_id")),
        ),
    )

    if isinstance(provenance, dict):
        _append_section(
            lines,
            "Code Provenance",
            (
                ("pipeline_version", provenance.get("pipeline_version")),
                ("git_commit", provenance.get("git_commit")),
                ("source_revision_state", provenance.get("source_revision_state")),
                ("config_hash", provenance.get("config_hash")),
                ("resolved_config_hash", provenance.get("resolved_config_hash")),
                ("effective_config_hash", provenance.get("effective_config_hash")),
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
        _append_section(lines, "Diagnostics", _diagnostics_section_items(diagnostics))

    return lines


def _diagnostics_section_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return (
        ("latest_status", diagnostics.get("latest_status")),
        ("latest_event_type", diagnostics.get("latest_event_type")),
        ("total_events", diagnostics.get("total_events")),
        ("execution_fingerprint", diagnostics.get("execution_fingerprint")),
        ("config_hash", diagnostics.get("config_hash")),
        ("resolved_config_hash", diagnostics.get("resolved_config_hash")),
        ("effective_config_hash", diagnostics.get("effective_config_hash")),
        ("git_commit", diagnostics.get("git_commit")),
        ("source_revision_state", diagnostics.get("source_revision_state")),
        ("code_provenance_state", diagnostics.get("code_provenance_state")),
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
        ("requested_exact_replay", diagnostics.get("requested_exact_replay")),
        (
            "exact_replay_support_boundary",
            diagnostics.get("exact_replay_support_boundary"),
        ),
        ("replay_family_contract", diagnostics.get("replay_family_contract")),
        ("replay_capability_reason", diagnostics.get("replay_capability_reason")),
        ("exact_replay_blockers", diagnostics.get("exact_replay_blockers")),
        ("append_mode_semantic_sinks", diagnostics.get("append_mode_semantic_sinks")),
        ("input_snapshot_ids", diagnostics.get("input_snapshot_ids")),
        (
            "input_snapshot_content_hashes",
            diagnostics.get("input_snapshot_content_hashes"),
        ),
        (
            "input_snapshot_identity_fingerprint",
            diagnostics.get("input_snapshot_identity_fingerprint"),
        ),
        ("exact_replay_anchors", diagnostics.get("exact_replay_anchors")),
        ("replay_mode", diagnostics.get("replay_mode")),
        ("replay_of_run_id", diagnostics.get("replay_of_run_id")),
        ("replay_of_manifest_id", diagnostics.get("replay_of_manifest_id")),
        ("replay_parentage", diagnostics.get("replay_parentage")),
        ("input_snapshot_count", diagnostics.get("input_snapshot_count")),
        ("input_snapshots", diagnostics.get("input_snapshots")),
        ("event_family_counts", diagnostics.get("event_family_counts")),
        ("event_type_counts", diagnostics.get("event_type_counts")),
        ("planned_artifact_count", diagnostics.get("planned_artifact_count")),
        ("published_artifact_count", diagnostics.get("published_artifact_count")),
        ("missing_artifact_links", diagnostics.get("missing_artifact_links")),
        ("lineage_fragment_ids", diagnostics.get("lineage_fragment_ids")),
        ("artifact_refs", diagnostics.get("artifact_refs")),
        ("produced_artifact_trace", diagnostics.get("produced_artifact_trace")),
        ("identity_graph_complete", diagnostics.get("identity_graph_complete")),
        ("dq_rule_ids", diagnostics.get("dq_rule_ids")),
        ("dq_dispositions", diagnostics.get("dq_dispositions")),
        ("dq_report_paths", diagnostics.get("dq_report_paths")),
        ("dq_violation_kinds", diagnostics.get("dq_violation_kinds")),
        ("cross_validation_rule_ids", diagnostics.get("cross_validation_rule_ids")),
        (
            "cross_validation_config_paths",
            diagnostics.get("cross_validation_config_paths"),
        ),
        (
            "cross_validation_quarantine_policy",
            diagnostics.get("cross_validation_quarantine_policy"),
        ),
        (
            "cross_validation_quarantine_replay_contract",
            diagnostics.get("cross_validation_quarantine_replay_contract"),
        ),
        ("occurrence_only_diagnostics", diagnostics.get("occurrence_only_diagnostics")),
        (
            "cross_validation_signal_present",
            diagnostics.get("cross_validation_signal_present"),
        ),
        ("correlation_anchor_gaps", diagnostics.get("correlation_anchor_gaps")),
        ("persistence_profile", diagnostics.get("persistence_profile")),
        (
            "reproducibility_audit_score",
            diagnostics.get("reproducibility_audit_score"),
        ),
        ("alert_signals", diagnostics.get("alert_signals")),
        ("next_steps", diagnostics.get("next_steps")),
    )


def _render_identity_graph_section(identity_graph: object) -> list[str]:
    """Render one explicit identity-graph reconstruction section."""
    lines: list[str] = []
    if not isinstance(identity_graph, dict):
        return lines
    _append_section(
        lines,
        "Identity Graph",
        (
            ("run_id", identity_graph.get("run_id")),
            ("manifest_id", identity_graph.get("manifest_id")),
            ("execution_fingerprint", identity_graph.get("execution_fingerprint")),
            ("config_hash", identity_graph.get("config_hash")),
            ("resolved_config_hash", identity_graph.get("resolved_config_hash")),
            ("effective_config_hash", identity_graph.get("effective_config_hash")),
            ("git_commit", identity_graph.get("git_commit")),
            ("source_revision_state", identity_graph.get("source_revision_state")),
            ("code_provenance_state", identity_graph.get("code_provenance_state")),
            ("contract_ref", identity_graph.get("contract_ref")),
            ("contract_version", identity_graph.get("contract_version")),
            ("replay_capability", identity_graph.get("replay_capability")),
            ("requested_exact_replay", identity_graph.get("requested_exact_replay")),
            (
                "exact_replay_support_boundary",
                identity_graph.get("exact_replay_support_boundary"),
            ),
            ("replay_family_contract", identity_graph.get("replay_family_contract")),
            (
                "replay_capability_reason",
                identity_graph.get("replay_capability_reason"),
            ),
            ("exact_replay_eligible", identity_graph.get("exact_replay_eligible")),
            ("exact_replay_blockers", identity_graph.get("exact_replay_blockers")),
            (
                "append_mode_semantic_sinks",
                identity_graph.get("append_mode_semantic_sinks"),
            ),
            ("input_snapshot_ids", identity_graph.get("input_snapshot_ids")),
            (
                "input_snapshot_content_hashes",
                identity_graph.get("input_snapshot_content_hashes"),
            ),
            (
                "input_snapshot_identity_fingerprint",
                identity_graph.get("input_snapshot_identity_fingerprint"),
            ),
            ("exact_replay_anchors", identity_graph.get("exact_replay_anchors")),
            ("replay_mode", identity_graph.get("replay_mode")),
            ("replay_of_run_id", identity_graph.get("replay_of_run_id")),
            ("replay_of_manifest_id", identity_graph.get("replay_of_manifest_id")),
            ("replay_parentage", identity_graph.get("replay_parentage")),
            ("input_snapshot_count", identity_graph.get("input_snapshot_count")),
            ("input_snapshots", identity_graph.get("input_snapshots")),
            ("planned_artifacts", identity_graph.get("planned_artifacts")),
            ("published_artifacts", identity_graph.get("published_artifacts")),
            (
                "produced_artifact_trace",
                identity_graph.get("produced_artifact_trace"),
            ),
            (
                "occurrence_only_diagnostics",
                identity_graph.get("occurrence_only_diagnostics"),
            ),
        ),
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
    lines.extend(_render_manifest_section(manifest))

    if lines:
        lines.append("")
    lines.extend(_render_ledger_section(ledger_entries))

    if lines and isinstance(ledger_entries, list) and ledger_entries:
        lines.append("")
    lines.extend(_render_diagnostics_section(diagnostics))

    identity_graph_lines = _render_identity_graph_section(identity_graph)
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
        f"  left_manifest_id: {_format_scalar(left_manifest_id)}",
        f"  right_manifest_id: {_format_scalar(right_manifest_id)}",
        f"  classification: {_format_scalar(payload.get('classification'))}",
        f"  semantic_equivalent: {_format_scalar(payload.get('semantic_equivalent'))}",
        f"  occurrence_only: {_format_scalar(payload.get('occurrence_only'))}",
        f"  replay_relationship: {_format_scalar(payload.get('replay_relationship'))}",
    ]
    for label in (
        "occurrence_difference_fields",
        "semantic_difference_fields",
        "noncanonical_difference_fields",
    ):
        value = payload.get(label)
        if value in (None, [], ()):
            continue
        rendered = _format_block(value)
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


def render_text_payload(payload: dict[str, object]) -> str:
    """Render CLI payload in human-readable text mode."""
    if "manifest" in payload:
        return render_show_payload(payload)
    if "differences" in payload:
        return render_diff_payload(payload)
    return json.dumps(payload, indent=2, default=str)
