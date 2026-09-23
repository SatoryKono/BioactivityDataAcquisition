"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re

from memory.graph.sync_pkg._core_convert import _is_claim_candidate
from memory.graph.sync_pkg._core_models import ClaimLineContext, NodeKey
from memory.graph.sync_pkg.add_claim_target_relation import _add_claim_target_relation
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.markdown_headings import _resolve_docs_reference_target
from memory.graph.sync_pkg.normalize_docs_repo_reference import (
    _markdown_heading_context,
    _normalize_docs_repo_reference,
)

__all__ = [
    "_add_claim_path_targets",
    "_claim_line_context",
    "_claim_section_context",
]


def _claim_line_context(raw_line: str) -> ClaimLineContext | None:
    stripped = raw_line.strip()
    if not _is_claim_candidate(stripped):
        return None
    return ClaimLineContext(
        stripped=stripped,
        clean_text=stripped.lstrip("-*0123456789. ").strip(),
    )


def _claim_section_context(text: str, raw_line: str) -> tuple[str | None, str | None]:
    line_offset = text.find(raw_line)
    return _markdown_heading_context(text, line_offset)


def _add_claim_path_targets(
    snapshot: GraphSnapshot,
    claim: NodeKey,
    source_node: NodeKey,
    stripped: str,
    *,
    section_title: str | None,
    section_anchor: str | None,
    line_number: int,
    path_pattern: re.Pattern[str],
) -> bool:
    claim_has_target = False
    for claim_match in path_pattern.finditer(stripped):
        normalized = _normalize_docs_repo_reference(claim_match.group(1))
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        _add_claim_target_relation(
            snapshot,
            claim,
            target,
            provenance="docs_claims",
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )
        claim_has_target = True
    return claim_has_target
