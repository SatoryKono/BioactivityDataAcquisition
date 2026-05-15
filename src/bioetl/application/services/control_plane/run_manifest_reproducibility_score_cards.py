"""Pure score-card builders for run-manifest reproducibility diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring_support import (
    bounded,
    string_items,
    supported_boundary_block_reason,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

JsonDict = dict[str, object]

PROFILE_SCORE_THRESHOLDS: dict[str, dict[str, int]] = {
    "degraded_observable": {},
    "replay_ready": {
        "determinism": 7,
        "run_identity": 8,
        "checkpoint_safety": 7,
        "replay_readiness": 7,
        "layer_consistency": 7,
    },
    "forensic_grade": {
        "determinism": 8,
        "run_identity": 8,
        "checkpoint_safety": 8,
        "lineage_completeness": 8,
        "replay_readiness": 8,
        "layer_consistency": 8,
    },
}

_BLOCKER_PRIORITY_ORDER: tuple[str, ...] = (
    "dependency_lock_hash_missing",
    "dependency_lock_provenance",
    "dependency_lock_provenance_missing",
    "exact_replay_capability",
    "exact_replay_not_eligible",
    "identity_graph_incomplete",
    "immutable_input_snapshots",
    "immutable_input_snapshots_missing",
    "missing_immutable_input_snapshots",
    "produced_artifact_trace",
)
_BLOCKER_PRIORITY_INDEX: dict[str, int] = {
    blocker: index for index, blocker in enumerate(_BLOCKER_PRIORITY_ORDER)
}


@dataclass(frozen=True, slots=True)
class ScoreCardRecord:
    category: str
    score: int
    evidence: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: str = "high"

    def to_dict(self) -> JsonDict:
        return {
            "score": self.score,
            "evidence": list(self.evidence),
            "blockers": list(self.blockers),
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
        }


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
    if summary.get("config_hash"):
        evidence.append("legacy_config_hash_exposed_as_compatibility_alias")
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


def evaluate_threshold_failures(
    *,
    thresholds: dict[str, int],
    category_scores: dict[str, JsonDict],
) -> list[JsonDict]:
    failures: list[JsonDict] = []
    for category, minimum_score in thresholds.items():
        score_payload = category_scores.get(category)
        actual_score = (
            score_payload.get("score") if isinstance(score_payload, dict) else None
        )
        if not isinstance(actual_score, int):
            failures.append(
                {
                    "category": category,
                    "required": minimum_score,
                    "actual": None,
                    "reason": "category_score_missing",
                }
            )
            continue
        if actual_score >= minimum_score:
            continue
        failures.append(
            {
                "category": category,
                "required": minimum_score,
                "actual": actual_score,
                "reason": "below_required_threshold",
            }
        )
    return failures


def overall_blockers(
    summary: JsonDict,
    score_cards: tuple[ScoreCardRecord, ...],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(string_items(summary.get("exact_replay_blockers")))
    persistence_profile = summary.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        blockers.extend(
            string_items(
                persistence_profile.get("required_profile_missing_requirements")
            )
        )
    for card in score_cards:
        blockers.extend(card.blockers)
    unique_blockers = list(dict.fromkeys(blockers))
    return sorted(
        unique_blockers,
        key=lambda blocker: (
            _BLOCKER_PRIORITY_INDEX.get(
                blocker,
                len(_BLOCKER_PRIORITY_INDEX) + unique_blockers.index(blocker),
            ),
        ),
    )


def overall_evidence_refs(score_cards: tuple[ScoreCardRecord, ...]) -> list[str]:
    refs: list[str] = []
    for card in score_cards:
        refs.extend(card.evidence_refs)
    return sorted(dict.fromkeys(refs))


def build_supported_boundary_verdict(
    *,
    summary: JsonDict,
    required_profile: str,
    threshold_failures: list[JsonDict],
) -> JsonDict:
    lineage_boundary = summary.get("lineage_closure_boundary")
    replay_family_contract = summary.get("replay_family_contract")

    lineage_supported = (
        bool(lineage_boundary.get("supported"))
        if isinstance(lineage_boundary, dict)
        else False
    )
    strict_exact_replay_supported = (
        bool(replay_family_contract.get("strict_exact_replay_supported"))
        if isinstance(replay_family_contract, dict)
        else False
    )
    replay_capability = str(summary.get("replay_capability") or "")
    persistence_profile = summary.get("persistence_profile")
    required_profile_satisfied = (
        bool(persistence_profile.get("required_profile_satisfied"))
        if isinstance(persistence_profile, dict)
        else False
    )
    blocked_outside_supported_boundary = not strict_exact_replay_supported
    has_supported_boundary_gaps = (
        bool(threshold_failures)
        or not required_profile_satisfied
        or replay_capability != "exact_replay_supported"
    )

    if blocked_outside_supported_boundary:
        verdict = "blocked_outside_supported_boundary"
        supported_boundary_satisfied = False
        reason = supported_boundary_block_reason(lineage_boundary)
    elif has_supported_boundary_gaps:
        verdict = "supported_boundary_gaps_present"
        supported_boundary_satisfied = False
        reason = "supported_boundary_requirements_not_met"
    else:
        verdict = "supported_boundary_satisfied"
        supported_boundary_satisfied = True
        reason = "supported_boundary_requirements_met"

    return {
        "scope": "supported_boundary_run",
        "supported_boundary_satisfied": supported_boundary_satisfied,
        "verdict": verdict,
        "reason": reason,
        "required_profile": required_profile,
        "replay_capability": replay_capability,
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_supported": lineage_supported,
    }


def build_global_reproducibility_claim(
    *,
    summary: JsonDict,
    evidence_refs: list[str],
) -> JsonDict:
    claim_refs = sorted(
        dict.fromkeys(
            [
                *evidence_refs,
                "diagnostics.exact_replay_support_boundary",
                "diagnostics.lineage_closure_boundary",
                "diagnostics.replay_family_contract",
            ]
        )
    )
    return {
        "scope": "project_wide_exact_replay",
        "claimed": False,
        "verdict": "universal_exact_replay_not_claimed",
        "reason": "published_contract_limits_exact_replay_to_supported_boundary",
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "evidence_refs": claim_refs,
    }


__all__ = [
    "PROFILE_SCORE_THRESHOLDS",
    "ScoreCardRecord",
    "build_global_reproducibility_claim",
    "build_supported_boundary_verdict",
    "evaluate_threshold_failures",
    "overall_blockers",
    "overall_evidence_refs",
    "score_checkpoint_safety",
    "score_determinism",
    "score_idempotency",
    "score_layer_consistency",
    "score_lineage_completeness",
    "score_replay_readiness",
    "score_run_identity",
]
