"""Shared types and thresholds for reproducibility score cards."""

from __future__ import annotations

from collections.abc import Iterable
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


def build_score_card_record(
    category: str,
    score: int,
    evidence: Iterable[str],
    blockers: Iterable[str],
    evidence_refs: Iterable[str],
) -> ScoreCardRecord:
    """Build one bounded score-card record through the canonical constructor."""
    items = tuple(evidence), tuple(blockers), tuple(evidence_refs)
    return ScoreCardRecord(category, max(0, min(10, score)), *items)


__all__ = [
    "PROFILE_SCORE_THRESHOLDS",
    "JsonDict",
    "ScoreCardRecord",
    "build_score_card_record",
]
