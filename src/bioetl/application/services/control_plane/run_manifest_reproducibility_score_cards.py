"""Pure score-card builders for run-manifest reproducibility diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_aggregation import (
    build_supported_boundary_verdict,
    evaluate_threshold_failures,
    overall_blockers,
    overall_evidence_refs,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    PROFILE_SCORE_THRESHOLDS,
    ScoreCardRecord,
    score_checkpoint_safety,
    score_determinism,
    score_idempotency,
    score_layer_consistency,
    score_lineage_completeness,
    score_replay_readiness,
    score_run_identity,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_claims import (
    build_executable_run_contract_claim,
    build_historical_replay_universe_exact_replay_claim,
)

JsonDict = dict[str, object]
_EXPORTED_SCORERS = (
    score_checkpoint_safety,
    score_determinism,
    score_idempotency,
    score_layer_consistency,
    score_lineage_completeness,
    score_replay_readiness,
    score_run_identity,
)
__all__ = [
    "PROFILE_SCORE_THRESHOLDS", "ScoreCardRecord",
    "build_executable_run_contract_claim",
    "build_historical_replay_universe_exact_replay_claim",
    "build_supported_boundary_verdict", "evaluate_threshold_failures",
    "overall_blockers", "overall_evidence_refs",
    *(scorer.__name__ for scorer in _EXPORTED_SCORERS),
]
