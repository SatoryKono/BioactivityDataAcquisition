"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_claim_target_relation import _add_claim_target_relation
from memory.graph.sync_pkg.docs_reference_exact_candidates import _resolve_claim_targets
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_claim_token_targets",
]


def _add_claim_token_targets(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    clean_text: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
) -> bool:
    claim_has_target = False
    for target, evidence_kind, confidence in _resolve_claim_targets(
        snapshot, clean_text
    ):
        _add_claim_target_relation(
            snapshot,
            claim,
            target,
            provenance="docs_claims",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )
        claim_has_target = True
    return claim_has_target
