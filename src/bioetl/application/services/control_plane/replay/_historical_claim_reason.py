"""Reason codes for historical replay universe exact-replay claims."""

from __future__ import annotations

__all__ = ["historical_universe_claim_reason"]


def historical_universe_claim_reason(
    *,
    fully_claimed: bool,
    exact_replay_supported: bool,
    durable_supported: bool,
) -> str:
    if fully_claimed:
        return "latest_historical_replay_universe_artifact_supports_universal_claim"
    if not exact_replay_supported:
        return "historical_replay_universe_artifact_blocks_universal_claim"
    if not durable_supported:
        return "durable_evidence_coverage_blocks_universal_claim"
    return "governed_full_corpus_gate_unsatisfied"
