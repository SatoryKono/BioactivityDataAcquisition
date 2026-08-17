"""Core category scorers for reproducibility score cards."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_types import (
    ScoreCardRecord as ScoreCardRecord,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_types import (
    build_score_card_record as build_score_card_record,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_types import (
    string_items as string_items,
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
    return build_score_card_record(
        "determinism",
        score,
        evidence,
        dict.fromkeys(blockers),
        dict.fromkeys(refs),
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
    return build_score_card_record("idempotency", score, evidence, blockers, refs)


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
    return build_score_card_record("run_identity", score, evidence, blockers, refs)


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
    return build_score_card_record("checkpoint_safety", score, evidence, blockers, refs)


__all__ = [
    "ScoreCardRecord",
    "build_score_card_record",
    "score_checkpoint_safety",
    "score_determinism",
    "score_idempotency",
    "score_run_identity",
    "string_items",
]
