"""Machine-readable reproducibility audit scoring for run-manifest inspection."""

from __future__ import annotations

from dataclasses import dataclass

JsonDict = dict[str, object]


@dataclass(frozen=True, slots=True)
class _ScoreCard:
    category: str
    score: int
    evidence: tuple[str, ...]

    def to_dict(self) -> JsonDict:
        return {
            "score": self.score,
            "evidence": list(self.evidence),
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
    overall = round(
        sum(card.score for card in score_cards) / max(len(score_cards), 1),
        1,
    )
    return {
        "schema_version": "1.0",
        "scale": "0-10",
        "overall_score": overall,
        "category_scores": category_scores,
        "source": "run_manifest_diagnostics",
    }


def _score_determinism(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 10
    if not summary.get("effective_config_hash"):
        score -= 2
        evidence.append("missing_effective_config_hash")
    else:
        evidence.append("effective_config_hash_present")
    if not summary.get("input_snapshot_ids"):
        score -= 2
        evidence.append("missing_immutable_input_snapshots")
    else:
        evidence.append("immutable_input_snapshots_present")
    if summary.get("exact_replay_blockers"):
        score -= 2
        evidence.append("exact_replay_blockers_present")
    return _ScoreCard("determinism", _bounded(score), tuple(evidence))


def _score_idempotency(summary: JsonDict) -> _ScoreCard:
    evidence = []
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
    return _ScoreCard("idempotency", _bounded(score), tuple(evidence))


def _score_run_identity(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 10
    required = (
        "manifest_id",
        "execution_fingerprint",
        "resolved_config_hash",
        "effective_config_hash",
        "effective_config_artifact_id",
        "contract_ref",
    )
    for field_name in required:
        if summary.get(field_name):
            evidence.append(f"{field_name}_present")
        else:
            score -= 1
            evidence.append(f"{field_name}_missing")
    return _ScoreCard("run_identity", _bounded(score), tuple(evidence))


def _score_checkpoint_safety(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 8
    resume_contract = summary.get("resume_contract")
    if isinstance(resume_contract, dict):
        applied_policy = resume_contract.get("applied_checkpoint_compatibility_policy")
        if applied_policy == "hard_fail":
            score += 1
            evidence.append("hard_fail_checkpoint_policy")
        if applied_policy == "legacy_observe":
            score -= 2
            evidence.append("legacy_observe_checkpoint_policy")
        if resume_contract.get("resume_requested"):
            evidence.append("resume_requested")
    else:
        score -= 1
        evidence.append("resume_contract_missing")
    return _ScoreCard("checkpoint_safety", _bounded(score), tuple(evidence))


def _score_lineage_completeness(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 10
    if not summary.get("identity_graph_complete"):
        score -= 2
        evidence.append("identity_graph_incomplete")
    if summary.get("missing_artifact_links", 0):
        score -= 2
        evidence.append("artifact_lineage_links_missing")
    if not summary.get("lineage_fragment_ids"):
        score -= 1
        evidence.append("no_lineage_fragments_observed")
    return _ScoreCard("lineage_completeness", _bounded(score), tuple(evidence))


def _score_replay_readiness(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 10
    if not summary.get("exact_replay_eligible"):
        score -= 3
        evidence.append("exact_replay_not_eligible")
    blockers = summary.get("exact_replay_blockers")
    if blockers:
        score -= min(len(blockers), 3) if isinstance(blockers, list) else 2
        evidence.append("exact_replay_blockers_present")
    if summary.get("replay_mode") == "rebuild_only":
        score -= 2
        evidence.append("rebuild_only_replay_mode")
    return _ScoreCard("replay_readiness", _bounded(score), tuple(evidence))


def _score_layer_consistency(summary: JsonDict) -> _ScoreCard:
    evidence = []
    score = 9
    if summary.get("config_hash") == summary.get("effective_config_hash"):
        score -= 1
        evidence.append("legacy_config_hash_alias_matches_effective_hash")
    if summary.get("resolved_config_hash") and summary.get("effective_config_hash"):
        evidence.append("resolved_and_effective_hashes_exposed")
    else:
        score -= 2
        evidence.append("resolved_or_effective_hash_missing")
    if summary.get("occurrence_only_diagnostics"):
        evidence.append("occurrence_only_diagnostics_exposed")
    return _ScoreCard("layer_consistency", _bounded(score), tuple(evidence))


def _bounded(score: int) -> int:
    return max(0, min(10, score))


__all__ = ["build_reproducibility_audit_scoring"]
