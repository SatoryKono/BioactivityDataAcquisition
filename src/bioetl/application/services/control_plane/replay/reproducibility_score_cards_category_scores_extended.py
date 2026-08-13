"""Extended category scorers for reproducibility score cards."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    ScoreCardRecord,
    build_score_card_record,
    string_items,
)

JsonDict = dict[str, object]


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
    return build_score_card_record(
        "lineage_completeness", score, evidence, blockers, refs
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
    return build_score_card_record(
        "replay_readiness",
        score,
        evidence,
        dict.fromkeys(blocker_items),
        refs,
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
    return build_score_card_record("layer_consistency", score, evidence, blockers, refs)


__all__ = [
    "score_layer_consistency",
    "score_lineage_completeness",
    "score_replay_readiness",
]
