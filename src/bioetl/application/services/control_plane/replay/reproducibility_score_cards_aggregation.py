"""Aggregation helpers for reproducibility score cards."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    JsonDict,
    ScoreCardRecord,
    string_items,
    supported_boundary_block_reason,
)

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
    "artifact_publication_closure",
    "produced_artifact_trace",
)
_BLOCKER_PRIORITY_INDEX: dict[str, int] = {
    blocker: index for index, blocker in enumerate(_BLOCKER_PRIORITY_ORDER)
}


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
        "scope": (
            "unsupported_boundary_run"
            if blocked_outside_supported_boundary
            else "supported_boundary_run"
        ),
        "supported_boundary_satisfied": supported_boundary_satisfied,
        "verdict": verdict,
        "reason": reason,
        "required_profile": required_profile,
        "replay_capability": replay_capability,
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "lineage_closure_supported": lineage_supported,
    }
