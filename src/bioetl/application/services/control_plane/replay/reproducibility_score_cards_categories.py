"""Category-level reproducibility score-card builders."""

from __future__ import annotations

from dataclasses import dataclass

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


# Import scorers after ScoreCardRecord so partial-module re-exports stay safe.
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_checkpoint_safety as score_checkpoint_safety,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_determinism as score_determinism,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_idempotency as score_idempotency,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_layer_consistency as score_layer_consistency,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_lineage_completeness as score_lineage_completeness,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_replay_readiness as score_replay_readiness,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (  # noqa: E402
    score_run_identity as score_run_identity,
)

__all__ = [
    "PROFILE_SCORE_THRESHOLDS",
    "ScoreCardRecord",
    "score_checkpoint_safety",
    "score_determinism",
    "score_idempotency",
    "score_layer_consistency",
    "score_lineage_completeness",
    "score_replay_readiness",
    "score_run_identity",
]
