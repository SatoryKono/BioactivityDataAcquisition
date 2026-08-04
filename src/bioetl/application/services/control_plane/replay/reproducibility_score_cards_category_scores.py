"""Re-export facade for category scorers used by score-card builders."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    score_checkpoint_safety as score_checkpoint_safety,
    score_determinism as score_determinism,
    score_idempotency as score_idempotency,
    score_run_identity as score_run_identity,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended import (
    score_layer_consistency as score_layer_consistency,
    score_lineage_completeness as score_lineage_completeness,
    score_replay_readiness as score_replay_readiness,
)
# Shared public scorer export names — also consumed by run-manifest score-card
# facade so the export roster is defined once (R0801 residual, issue #7398).
CATEGORY_SCORER_EXPORTS: tuple[str, ...] = (
    "score_checkpoint_safety",
    "score_determinism",
    "score_idempotency",
    "score_layer_consistency",
    "score_lineage_completeness",
    "score_replay_readiness",
    "score_run_identity",
)
# Backward-compatible private alias for intermediate facades.
_CATEGORY_SCORER_EXPORTS = CATEGORY_SCORER_EXPORTS

__all__ = [
    "CATEGORY_SCORER_EXPORTS",
    "_CATEGORY_SCORER_EXPORTS",
    *CATEGORY_SCORER_EXPORTS,
]
