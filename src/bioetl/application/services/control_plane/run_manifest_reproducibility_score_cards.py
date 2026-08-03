"""Pure score-card builders for run-manifest reproducibility diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_aggregation import (
    build_supported_boundary_verdict,
    evaluate_threshold_failures,
    overall_blockers,
    overall_evidence_refs,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    PROFILE_SCORE_THRESHOLDS as PROFILE_SCORE_THRESHOLDS,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    ScoreCardRecord as ScoreCardRecord,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_checkpoint_safety as score_checkpoint_safety,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_determinism as score_determinism,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_idempotency as score_idempotency,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_layer_consistency as score_layer_consistency,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_lineage_completeness as score_lineage_completeness,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_replay_readiness as score_replay_readiness,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_categories import (
    score_run_identity as score_run_identity,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_claims import (
    build_executable_run_contract_claim as build_executable_run_contract_claim,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_claims import (
    build_historical_replay_universe_exact_replay_claim as build_historical_replay_universe_exact_replay_claim,
)

JsonDict = dict[str, object]
__all__ = [
    "PROFILE_SCORE_THRESHOLDS",
    "ScoreCardRecord",
    "build_executable_run_contract_claim",
    "build_historical_replay_universe_exact_replay_claim",
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
