"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_claim_fallback_target",
    "_add_claim_target_relation",
]


def _add_claim_target_relation(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    target: NodeKey,
    *,
    provenance: str,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
    evidence_kind: str,
    confidence: str,
    doc_reference: str | None = None,
) -> None:
    snapshot.add_relation(
        claim,
        "ASSERTS_ABOUT",
        target,
        provenance=provenance,
        doc_reference=doc_reference,
        evidence_kind=evidence_kind,
        confidence=confidence,
        section_title=section_title,
        section_anchor=section_anchor,
        line_number=line_number,
    )


def _add_claim_fallback_target(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    source_path: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
) -> None:
    file_surface_key = NodeKey("file_surface", source_path)
    if file_surface_key in snapshot.nodes:
        snapshot.add_relation(
            claim,
            "ASSERTS_ABOUT",
            file_surface_key,
            provenance="docs_claims_fallback",
            evidence_kind="source_document",
            confidence="low",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
        )
