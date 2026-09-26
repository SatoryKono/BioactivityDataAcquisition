"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.adr_title import _doc_reference_context
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_doc_describes_relation",
]


def _add_doc_describes_relation(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    target: NodeKey,
    text: str,
    offset: int,
    *,
    doc_reference: str,
    evidence_kind: str,
    confidence: str,
) -> None:
    section_title, section_anchor, line_number = _doc_reference_context(text, offset)
    snapshot.add_relation(
        source_node,
        "DESCRIBES",
        target,
        provenance="docs_code_drift",
        doc_reference=doc_reference,
        evidence_kind=evidence_kind,
        confidence=confidence,
        section_title=section_title,
        section_anchor=section_anchor,
        line_number=line_number,
    )
