"""Individual category scorers for reproducibility score cards."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    ScoreCardRecord,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring_support import (
    bounded,
    string_items,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

JsonDict = dict[str, object]


def score_determinism(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = ["diagnostics.effective_config_hash", "diagnostics.input_snapshot_ids"]
    score = 10
    if not summary.get("effective_config_hash"):
        score -= 2
        evidence.append("missing_effective_config_hash")
        blockers.append("missing_effective_config_hash")
    else:
        evidence.append("effective_config_hash_present")
    if not summary.get("input_snapshot_ids"):
        score -= 2
        evidence.append("missing_immutable_input_snapshots")
        blockers.append("missing_immutable_input_snapshots")
    else:
        evidence.append("immutable_input_snapshots_present")
    if summary.get("exact_replay_blockers"):
        score -= 2
        evidence.append("exact_replay_blockers_present")
        blockers.extend(string_items(summary.get("exact_replay_blockers")))
        refs.append("diagnostics.exact_replay_blockers")
    return ScoreCardRecord(
        "determinism",
        bounded(score),
        tuple(evidence),
        tuple(dict.fromkeys(blockers)),
        tuple(dict.fromkeys(refs)),
    )


def score_idempotency(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = ["diagnostics.exact_replay_eligible", "diagnostics.artifact_refs"]
    score = 7
    if summary.get("exact_replay_eligible"):
        score += 2
        evidence.append("exact_replay_eligible")
    if summary.get("published_artifact_count", 0) == 0:
        score -= 1
        evidence.append("no_published_artifacts_observed")
    if summary.get("artifact_publication_closure") not in {None, "closed"}:
        score -= 2
        evidence.append("artifact_publication_closure_not_closed")
        blockers.append("artifact_publication_closure")
    if summary.get("missing_artifact_links", 0):
        score -= 2
        evidence.append("missing_artifact_links_present")
        blockers.append("missing_artifact_links_present")
    return ScoreCardRecord(
        "idempotency",
        bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def score_run_identity(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = []
    score = 10
    required = (
        "manifest_id",
        "execution_fingerprint",
        "resolved_config_hash",
        "effective_config_hash",
        "effective_config_artifact_id",
        "contract_ref",
        "git_commit",
        "source_revision_state",
        "dependency_lock_hash",
    )
    for field_name in required:
        refs.append(f"diagnostics.{field_name}")
        if summary.get(field_name):
            evidence.append(f"{field_name}_present")
        else:
            score -= 1
            evidence.append(f"{field_name}_missing")
            blockers.append(f"{field_name}_missing")
    return ScoreCardRecord(
        "run_identity",
        bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def score_checkpoint_safety(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = ["diagnostics.resume_contract"]
    score = 8
    required_profile = str(
        summary.get("required_persistence_profile") or "degraded_observable"
    )
    resume_contract = summary.get("resume_contract")
    if isinstance(resume_contract, dict):
        applied_policy = resume_contract.get("applied_checkpoint_compatibility_policy")
        if applied_policy == "hard_fail":
            score += 1
            evidence.append("hard_fail_checkpoint_policy")
        if (
            required_profile in STRICT_PERSISTENCE_PROFILES
            and applied_policy != "hard_fail"
        ):
            score -= 1
            evidence.append("checkpoint_policy_below_profile_minimum")
            blockers.append("checkpoint_policy_below_profile_minimum")
        if resume_contract.get("resume_requested"):
            evidence.append("resume_requested")
    else:
        score -= 1
        evidence.append("resume_contract_missing")
        blockers.append("resume_contract_missing")
    return ScoreCardRecord(
        "checkpoint_safety",
        bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def score_lineage_completeness(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = [
        "diagnostics.identity_graph_complete",
        "diagnostics.lineage_fragment_ids",
        "diagnostics.lineage_closure_boundary",
    ]
    score = 10
    if not summary.get("identity_graph_complete"):
        score -= 2
        evidence.append("identity_graph_incomplete")
        blockers.append("identity_graph_incomplete")
    lineage_boundary = summary.get("lineage_closure_boundary")
    if isinstance(lineage_boundary, dict) and not bool(
        lineage_boundary.get("supported")
    ):
        score -= 2
        evidence.append("lineage_closure_boundary_unsupported")
        blockers.append("lineage_closure_boundary_unsupported")
    if summary.get("missing_artifact_links", 0):
        score -= 2
        evidence.append("artifact_lineage_links_missing")
        blockers.append("artifact_lineage_links_missing")
    if not summary.get("lineage_fragment_ids"):
        score -= 1
        evidence.append("no_lineage_fragments_observed")
    return ScoreCardRecord(
        "lineage_completeness",
        bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def score_replay_readiness(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blocker_items = []
    refs = [
        "diagnostics.exact_replay_eligible",
        "diagnostics.exact_replay_blockers",
        "diagnostics.replay_mode",
    ]
    score = 10
    if not summary.get("exact_replay_eligible"):
        score -= 3
        evidence.append("exact_replay_not_eligible")
        blocker_items.append("exact_replay_not_eligible")
    exact_replay_blockers = summary.get("exact_replay_blockers")
    if exact_replay_blockers:
        score -= (
            min(len(exact_replay_blockers), 3)
            if isinstance(exact_replay_blockers, list)
            else 2
        )
        evidence.append("exact_replay_blockers_present")
        blocker_items.extend(string_items(exact_replay_blockers))
    if summary.get("replay_mode") == "rebuild_only":
        score -= 2
        evidence.append("rebuild_only_replay_mode")
        blocker_items.append("rebuild_only_replay_mode")
    if summary.get("artifact_publication_closure") not in {None, "closed"}:
        score -= 2
        evidence.append("artifact_publication_closure_not_closed")
        blocker_items.append("artifact_publication_closure")
    return ScoreCardRecord(
        "replay_readiness",
        bounded(score),
        tuple(evidence),
        tuple(dict.fromkeys(blocker_items)),
        tuple(refs),
    )


def score_layer_consistency(summary: JsonDict) -> ScoreCardRecord:
    evidence = []
    blockers = []
    refs = [
        "diagnostics.resolved_config_hash",
        "diagnostics.effective_config_hash",
        "diagnostics.reproducibility_diagnostics.effective_config.diff_policy",
        "diagnostics.occurrence_only_diagnostics",
    ]
    score = 9
    if summary.get("resolved_config_hash"):
        evidence.append("resolved_config_hash_exposed")
    if summary.get("effective_config_hash"):
        evidence.append("effective_config_hash_exposed")
    if summary.get("resolved_config_hash") and summary.get("effective_config_hash"):
        evidence.append("resolved_and_effective_hashes_exposed")
    else:
        score -= 2
        evidence.append("resolved_or_effective_hash_missing")
        blockers.append("resolved_or_effective_hash_missing")
    if summary.get("occurrence_only_diagnostics"):
        evidence.append("occurrence_only_diagnostics_exposed")
    return ScoreCardRecord(
        "layer_consistency",
        bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


__all__ = [
    "score_checkpoint_safety",
    "score_determinism",
    "score_idempotency",
    "score_layer_consistency",
    "score_lineage_completeness",
    "score_replay_readiness",
    "score_run_identity",
]
