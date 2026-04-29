"""Machine-readable reproducibility audit scoring for run-manifest inspection."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

JsonDict = dict[str, object]

_PROFILE_SCORE_THRESHOLDS: dict[str, dict[str, int]] = {
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


@dataclass(frozen=True, slots=True)
class _ScoreCard:
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


def build_reproducibility_audit_scoring(summary: JsonDict) -> JsonDict:
    """Build deterministic audit scores from diagnostics evidence."""
    score_cards = (
        _score_determinism(summary),
        _score_idempotency(summary),
        _score_run_identity(summary),
        _score_checkpoint_safety(summary),
        _score_lineage_completeness(summary),
        _score_replay_readiness(summary),
        _score_layer_consistency(summary),
    )
    category_scores = {card.category: card.to_dict() for card in score_cards}
    required_profile = str(
        summary.get("required_persistence_profile") or "degraded_observable"
    )
    thresholds = dict(_PROFILE_SCORE_THRESHOLDS.get(required_profile, {}))
    threshold_failures = _evaluate_threshold_failures(
        thresholds=thresholds,
        category_scores=category_scores,
    )
    overall = round(
        sum(card.score for card in score_cards) / max(len(score_cards), 1),
        1,
    )
    return {
        "schema_version": "1.0",
        "contract_version": summary.get("contract_version"),
        "scale": "0-10",
        "required_profile": required_profile,
        "overall_score": overall,
        "category_scores": category_scores,
        "thresholds": thresholds,
        "threshold_failures": threshold_failures,
        "thresholds_satisfied": not threshold_failures,
        "blockers": _overall_blockers(summary, score_cards),
        "evidence_refs": _overall_evidence_refs(score_cards),
        "scored_at": summary.get("manifest_created_at"),
        "source": "run_manifest_diagnostics",
    }


def _score_determinism(summary: JsonDict) -> _ScoreCard:
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
        blockers.extend(_string_items(summary.get("exact_replay_blockers")))
        refs.append("diagnostics.exact_replay_blockers")
    return _ScoreCard(
        "determinism",
        _bounded(score),
        tuple(evidence),
        tuple(dict.fromkeys(blockers)),
        tuple(dict.fromkeys(refs)),
    )


def _score_idempotency(summary: JsonDict) -> _ScoreCard:
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
    return _ScoreCard(
        "idempotency",
        _bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def _score_run_identity(summary: JsonDict) -> _ScoreCard:
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
    )
    for field_name in required:
        refs.append(f"diagnostics.{field_name}")
        if summary.get(field_name):
            evidence.append(f"{field_name}_present")
        else:
            score -= 1
            evidence.append(f"{field_name}_missing")
            blockers.append(f"{field_name}_missing")
    return _ScoreCard(
        "run_identity",
        _bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def _score_checkpoint_safety(summary: JsonDict) -> _ScoreCard:
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
        requested_policy = resume_contract.get(
            "requested_checkpoint_compatibility_policy"
        )
        if applied_policy == "hard_fail":
            score += 1
            evidence.append("hard_fail_checkpoint_policy")
        if applied_policy == "legacy_observe":
            score -= 2
            evidence.append("legacy_observe_checkpoint_policy")
            blockers.append("legacy_observe_checkpoint_policy")
        if required_profile in STRICT_PERSISTENCE_PROFILES and requested_policy in {
            "observe",
            "legacy_observe",
        }:
            score -= 1
            evidence.append("checkpoint_policy_below_profile_minimum")
            blockers.append("checkpoint_policy_below_profile_minimum")
        if resume_contract.get("resume_requested"):
            evidence.append("resume_requested")
    else:
        score -= 1
        evidence.append("resume_contract_missing")
        blockers.append("resume_contract_missing")
    return _ScoreCard(
        "checkpoint_safety",
        _bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def _score_lineage_completeness(summary: JsonDict) -> _ScoreCard:
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
    return _ScoreCard(
        "lineage_completeness",
        _bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def _score_replay_readiness(summary: JsonDict) -> _ScoreCard:
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
        blocker_items.extend(_string_items(exact_replay_blockers))
    if summary.get("replay_mode") == "rebuild_only":
        score -= 2
        evidence.append("rebuild_only_replay_mode")
        blocker_items.append("rebuild_only_replay_mode")
    return _ScoreCard(
        "replay_readiness",
        _bounded(score),
        tuple(evidence),
        tuple(dict.fromkeys(blocker_items)),
        tuple(refs),
    )


def _score_layer_consistency(summary: JsonDict) -> _ScoreCard:
    evidence = []
    blockers = []
    refs = [
        "diagnostics.config_hash",
        "diagnostics.resolved_config_hash",
        "diagnostics.effective_config_hash",
        "diagnostics.occurrence_only_diagnostics",
    ]
    score = 9
    if summary.get("config_hash") == summary.get("resolved_config_hash"):
        evidence.append("legacy_config_hash_alias_matches_resolved_hash")
    elif summary.get("config_hash") and summary.get("resolved_config_hash"):
        evidence.append("legacy_config_hash_alias_semantics_ambiguous")
    if summary.get("resolved_config_hash") and summary.get("effective_config_hash"):
        evidence.append("resolved_and_effective_hashes_exposed")
    else:
        score -= 2
        evidence.append("resolved_or_effective_hash_missing")
        blockers.append("resolved_or_effective_hash_missing")
    if summary.get("occurrence_only_diagnostics"):
        evidence.append("occurrence_only_diagnostics_exposed")
    return _ScoreCard(
        "layer_consistency",
        _bounded(score),
        tuple(evidence),
        tuple(blockers),
        tuple(refs),
    )


def _bounded(score: int) -> int:
    return max(0, min(10, score))


def _string_items(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item is not None)


def _evaluate_threshold_failures(
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


def _overall_blockers(
    summary: JsonDict,
    score_cards: tuple[_ScoreCard, ...],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(_string_items(summary.get("exact_replay_blockers")))
    persistence_profile = summary.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        blockers.extend(
            _string_items(
                persistence_profile.get("required_profile_missing_requirements")
            )
        )
    for card in score_cards:
        blockers.extend(card.blockers)
    return sorted(dict.fromkeys(blockers))


def _overall_evidence_refs(score_cards: tuple[_ScoreCard, ...]) -> list[str]:
    refs: list[str] = []
    for card in score_cards:
        refs.extend(card.evidence_refs)
    return sorted(dict.fromkeys(refs))


__all__ = ["build_reproducibility_audit_scoring"]
