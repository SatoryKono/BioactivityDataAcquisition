"""Private diagnostics renderers for run-manifest CLI output."""

from __future__ import annotations

from bioetl.interfaces.cli.commands._run_manifest_output_support import (
    _items_from_keys,
    _JsonRenderer,
    append_section,
)


def _diagnostics_core_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return _items_from_keys(
        diagnostics,
        "latest_status",
        "latest_event_type",
        "total_events",
        "execution_fingerprint",
        "resolved_config_hash",
        "effective_config_hash",
        "config_hash",
        "source_fingerprint",
        "git_commit",
        "source_revision_state",
        "dependency_lock_state",
        "dependency_lock_hash",
        "code_provenance_state",
        "contract_ref",
        "contract_version",
        "normalization_profile_ref",
        "normalization_profile_version",
        "normalization_profile_hash",
        "dq_policy_ref",
        "rule_bundle_version",
    )


def _diagnostics_replay_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return _items_from_keys(
        diagnostics,
        "replay_readiness_verdict",
        "replay_resume_rebuild_verdict",
        "replay_next_action",
        "effective_config_artifact_id",
        "dq_contract_compatibility_hash",
        "operator_replay_mode",
        "requested_exact_replay",
        "exact_replay_support_boundary",
        "replay_family_contract",
        "strict_replay_runtime_verdict",
        "replay_support_scope",
        "replay_support_reason",
        "replay_capability_reason",
        "exact_replay_blockers",
        "append_mode_semantic_sinks",
        "snapshot_status",
        "input_snapshot_ids",
        "input_snapshot_content_hashes",
        "input_snapshot_identity_fingerprint",
        "exact_replay_anchors",
        "replay_mode",
        "continuation_mode",
        "resume_contract",
        "replay_of_run_id",
        "replay_of_manifest_id",
        "replay_parentage",
        "input_snapshot_count",
        "input_snapshots",
    )


def _diagnostics_artifact_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return _items_from_keys(
        diagnostics,
        "event_family_counts",
        "event_type_counts",
        "planned_artifact_count",
        "published_artifact_count",
        "missing_artifact_links",
        "lineage_fragment_ids",
        "artifact_refs",
        "produced_artifact_trace",
        "identity_graph_complete",
    )


def _diagnostics_dq_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return _items_from_keys(
        diagnostics,
        "dq_rule_ids",
        "dq_dispositions",
        "dq_report_paths",
        "dq_violation_kinds",
        "cross_validation_rule_ids",
        "cross_validation_config_paths",
        "cross_validation_quarantine_policy",
        "cross_validation_quarantine_replay_contract",
        "occurrence_only_diagnostics",
        "cross_validation_signal_present",
        "correlation_anchor_gaps",
    )


def _diagnostics_section_items(
    diagnostics: dict[str, object],
) -> tuple[tuple[str, object], ...]:
    return (
        *_diagnostics_core_items(diagnostics),
        *_diagnostics_replay_items(diagnostics),
        *_diagnostics_artifact_items(diagnostics),
        *_diagnostics_dq_items(diagnostics),
        ("persistence_profile", diagnostics.get("persistence_profile")),
        (
            "replay_capability_assessment",
            diagnostics.get("replay_capability_assessment"),
        ),
        (
            "reproducibility_diagnostics",
            diagnostics.get("reproducibility_diagnostics"),
        ),
        (
            "reproducibility_audit_score",
            diagnostics.get("reproducibility_audit_score"),
        ),
        (
            "historical_replay_universe_governed_full_corpus_gate",
            diagnostics.get("historical_replay_universe_governed_full_corpus_gate"),
        ),
        (
            "historical_replay_universe_exact_replay_claim",
            diagnostics.get("historical_replay_universe_exact_replay_claim"),
        ),
        (
            "executable_run_contract_claim",
            diagnostics.get("executable_run_contract_claim"),
        ),
        (
            "authoritative_replay_dossier",
            diagnostics.get("authoritative_replay_dossier"),
        ),
        ("alert_signals", diagnostics.get("alert_signals")),
        ("next_steps", diagnostics.get("next_steps")),
    )


def render_diagnostics_section(
    diagnostics: dict[str, object],
    *,
    json_renderer: _JsonRenderer,
) -> list[str]:
    """Render diagnostics section."""
    lines: list[str] = []
    append_section(
        lines,
        "Diagnostics",
        _diagnostics_section_items(diagnostics),
        json_renderer=json_renderer,
    )
    return lines


def render_identity_graph_section(
    identity_graph: dict[str, object],
    *,
    json_renderer: _JsonRenderer,
) -> list[str]:
    """Render one explicit identity-graph reconstruction section."""
    lines: list[str] = []
    append_section(
        lines,
        "Identity Graph",
        _items_from_keys(
            identity_graph,
            "run_id",
            "manifest_id",
            "execution_fingerprint",
            "config_hash",
            "resolved_config_hash",
            "effective_config_hash",
            "source_fingerprint",
            "git_commit",
            "source_revision_state",
            "dependency_lock_state",
            "dependency_lock_hash",
            "code_provenance_state",
            "contract_ref",
            "contract_version",
            "replay_capability",
            "operator_replay_mode",
            "requested_exact_replay",
            "replay_readiness_verdict",
            "replay_resume_rebuild_verdict",
            "replay_next_action",
            "exact_replay_support_boundary",
            "replay_family_contract",
            "strict_replay_runtime_verdict",
            "replay_support_scope",
            "replay_support_reason",
            "replay_capability_reason",
            "exact_replay_eligible",
            "exact_replay_blockers",
            "append_mode_semantic_sinks",
            "snapshot_status",
            "input_snapshot_ids",
            "input_snapshot_content_hashes",
            "input_snapshot_identity_fingerprint",
            "exact_replay_anchors",
            "replay_mode",
            "continuation_mode",
            "replay_of_run_id",
            "replay_of_manifest_id",
            "replay_parentage",
            "input_snapshot_count",
            "input_snapshots",
            "planned_artifacts",
            "published_artifacts",
            "produced_artifact_trace",
            "occurrence_only_diagnostics",
            "authoritative_replay_dossier",
        ),
        json_renderer=json_renderer,
    )
    return lines
