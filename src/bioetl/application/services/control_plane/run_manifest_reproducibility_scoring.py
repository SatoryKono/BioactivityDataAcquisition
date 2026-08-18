"""Machine-readable reproducibility audit scoring for run-manifest inspection."""

from __future__ import annotations

from bioetl.application.services.control_plane.run_manifest_reproducibility_score_cards import (
    PROFILE_SCORE_THRESHOLDS,
    build_executable_run_contract_claim,
    build_historical_replay_universe_exact_replay_claim,
    build_supported_boundary_verdict,
    evaluate_threshold_failures,
    overall_blockers,
    overall_evidence_refs,
    score_checkpoint_safety,
    score_determinism,
    score_idempotency,
    score_layer_consistency,
    score_lineage_completeness,
    score_replay_readiness,
    score_run_identity,
)

JsonDict = dict[str, object]


def build_reproducibility_audit_scoring(summary: JsonDict) -> JsonDict:
    """Build deterministic audit scores from diagnostics evidence."""
    score_cards = (
        score_determinism(summary),
        score_idempotency(summary),
        score_run_identity(summary),
        score_checkpoint_safety(summary),
        score_lineage_completeness(summary),
        score_replay_readiness(summary),
        score_layer_consistency(summary),
    )
    category_scores = {card.category: card.to_dict() for card in score_cards}
    required_profile = str(
        summary.get("required_persistence_profile") or "degraded_observable"
    )
    threshold_failures: list[dict[str, object]]
    if required_profile not in PROFILE_SCORE_THRESHOLDS:
        thresholds: dict[str, int] = {}
        threshold_failures = [
            {
                "category": "required_profile",
                "required": None,
                "actual": required_profile,
                "reason": "unknown_required_persistence_profile",
            }
        ]
    else:
        thresholds = dict(PROFILE_SCORE_THRESHOLDS[required_profile])
        threshold_failures = evaluate_threshold_failures(
            thresholds=thresholds,
            category_scores=category_scores,
        )
    overall = round(
        sum(card.score for card in score_cards) / max(len(score_cards), 1),
        1,
    )
    blockers = overall_blockers(summary, score_cards)
    evidence_refs = overall_evidence_refs(score_cards)
    supported_boundary_verdict = build_supported_boundary_verdict(
        summary=summary,
        required_profile=required_profile,
        threshold_failures=threshold_failures,
    )
    return {
        "schema_version": "2.0",
        "contract_version": summary.get("contract_version"),
        "scale": "0-10",
        "required_profile": required_profile,
        "score_scope": supported_boundary_verdict.get("scope"),
        "overall_score": overall,
        "category_scores": category_scores,
        "thresholds": thresholds,
        "threshold_failures": threshold_failures,
        "thresholds_satisfied": not threshold_failures,
        "blockers": blockers,
        "evidence_refs": evidence_refs,
        "supported_boundary_verdict": supported_boundary_verdict,
        "historical_replay_universe_exact_replay_claim": (
            build_historical_replay_universe_exact_replay_claim(
                summary=summary,
                evidence_refs=evidence_refs,
            )
        ),
        "executable_run_contract_claim": build_executable_run_contract_claim(
            summary=summary,
            evidence_refs=evidence_refs,
        ),
        "scored_at": summary.get("manifest_created_at"),
        "source": "run_manifest_diagnostics",
    }


__all__ = ["build_reproducibility_audit_scoring"]
