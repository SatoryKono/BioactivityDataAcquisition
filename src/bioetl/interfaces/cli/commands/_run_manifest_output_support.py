"""Private helper renderers for run-manifest CLI text output."""

from __future__ import annotations

from collections.abc import Callable, Iterable

type _JsonRenderer = Callable[[object], list[str]]


def format_scalar(value: object) -> str:
    """Format one scalar value for text-mode CLI output."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def format_block(
    value: object,
    *,
    json_renderer: _JsonRenderer,
) -> list[str]:
    """Format nested values as one or more human-readable text lines."""
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        return json_renderer(value)
    if isinstance(value, list):
        if not value:
            return ["[]"]
        if all(not isinstance(item, (dict, list)) for item in value):
            return [format_scalar(item) for item in value]
        return json_renderer(value)
    return [format_scalar(value)]


def append_section(
    lines: list[str],
    title: str,
    items: Iterable[tuple[str, object]],
    *,
    json_renderer: _JsonRenderer,
) -> None:
    """Append a titled section to text output."""
    filtered = [(label, value) for label, value in items if value not in (None, [], {})]
    if not filtered:
        return
    if lines:
        lines.append("")
    lines.append(title)
    for label, value in filtered:
        rendered = format_block(value, json_renderer=json_renderer)
        if len(rendered) == 1:
            lines.append(f"  {label}: {rendered[0]}")
            continue
        lines.append(f"  {label}:")
        lines.extend(f"    {line}" for line in rendered)


def render_manifest_section(
    manifest: dict[str, object],
    *,
    json_renderer: _JsonRenderer,
) -> list[str]:
    """Render manifest section."""
    lines: list[str] = []
    provenance = manifest.get("code_provenance", {})

    append_section(
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
        json_renderer=json_renderer,
    )

    if isinstance(provenance, dict):
        append_section(
            lines,
            "Code Provenance",
            (
                ("pipeline_version", provenance.get("pipeline_version")),
                ("git_commit", provenance.get("git_commit")),
                ("source_revision_state", provenance.get("source_revision_state")),
                ("dependency_lock_hash", provenance.get("dependency_lock_hash")),
                ("config_hash", provenance.get("config_hash")),
                ("resolved_config_hash", provenance.get("resolved_config_hash")),
                ("effective_config_hash", provenance.get("effective_config_hash")),
            ),
            json_renderer=json_renderer,
        )

    append_section(
        lines,
        "Execution Inputs",
        (
            ("launch_context", manifest.get("launch_context")),
            ("runtime_config", manifest.get("runtime_config")),
            ("resolved_config", manifest.get("resolved_config")),
            ("source_refs", manifest.get("source_refs")),
            ("planned_artifacts", manifest.get("planned_artifacts")),
        ),
        json_renderer=json_renderer,
    )
    return lines


def render_ledger_section(ledger_entries: list[object]) -> list[str]:
    """Render ledger section."""
    lines: list[str] = []
    if ledger_entries:
        lines.append("Ledger")
        lines.append(f"  entries: {len(ledger_entries)}")
        for entry in ledger_entries:
            if not isinstance(entry, dict):
                lines.append(f"  - {format_scalar(entry)}")
                continue
            summary = f"{entry.get('occurred_at', '?')} {entry.get('event_type', '?')}"
            stage = entry.get("stage")
            status = entry.get("status")
            if stage is not None:
                summary += f" stage={stage}"
            if status is not None:
                summary += f" status={status}"
            lines.append(f"  - {summary}")
        return lines
    append_section(lines, "Ledger", (("entries", 0),), json_renderer=lambda _: [])
    return lines


def _dict_value(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _items_from_keys(
    payload: dict[str, object],
    *keys: str,
) -> tuple[tuple[str, object], ...]:
    return tuple((key, payload.get(key)) for key in keys)


def render_reproducibility_compact_section(
    diagnostics: dict[str, object],
    *,
    json_renderer: _JsonRenderer,
) -> list[str]:
    """Render high-signal reproducibility diagnostics before raw nested details."""
    reproducibility = diagnostics.get("reproducibility_diagnostics")
    if not isinstance(reproducibility, dict):
        return []

    policy = _dict_value(reproducibility, "policy")
    capability_assessment = _dict_value(policy, "capability_assessment")
    effective_config = _dict_value(reproducibility, "effective_config")
    effective_semantic = _dict_value(effective_config, "semantic")
    effective_diff_policy = _dict_value(effective_config, "diff_policy")
    checkpoint_anchors = _dict_value(reproducibility, "checkpoint_anchors")
    resume_anchor_comparison = _dict_value(
        checkpoint_anchors,
        "resume_anchor_comparison",
    )

    lines: list[str] = []
    append_section(
        lines,
        "Reproducibility",
        (
            (
                "required_persistence_profile",
                policy.get("required_persistence_profile"),
            ),
            ("attained_profile", policy.get("attained_profile")),
            ("replay_capability", policy.get("replay_capability")),
            ("mode", policy.get("operator_replay_mode")),
            ("continuation_mode", policy.get("continuation_mode")),
            (
                "replay_capability_reason",
                policy.get("replay_capability_reason"),
            ),
            (
                "snapshot_status",
                _dict_value(reproducibility, "semantic_identity").get(
                    "snapshot_status"
                ),
            ),
            (
                "required_profile_satisfied",
                policy.get(
                    "required_profile_satisfied",
                    capability_assessment.get("required_profile_satisfied"),
                ),
            ),
            (
                "blocking_gaps",
                policy.get("exact_replay_blockers")
                or capability_assessment.get("blocking_gaps"),
            ),
            (
                "effective_config_artifact_id",
                effective_semantic.get("effective_config_artifact_id"),
            ),
            (
                "effective_config_hash",
                effective_semantic.get("effective_config_hash"),
            ),
            (
                "effective_config_semantic_anchor",
                effective_diff_policy.get("semantic_anchor"),
            ),
            (
                "effective_config_occurrence_fields",
                effective_diff_policy.get("occurrence_fields"),
            ),
            (
                "checkpoint_identity_present",
                resume_anchor_comparison.get("checkpoint_identity_present"),
            ),
            (
                "checkpoint_matching_fields",
                resume_anchor_comparison.get("matching_fields"),
            ),
            (
                "checkpoint_mismatched_fields",
                resume_anchor_comparison.get("mismatched_fields"),
            ),
            (
                "checkpoint_missing_current_fields",
                resume_anchor_comparison.get("missing_current_fields"),
            ),
            (
                "checkpoint_missing_checkpoint_fields",
                resume_anchor_comparison.get("missing_checkpoint_fields"),
            ),
        ),
        json_renderer=json_renderer,
    )
    return lines
