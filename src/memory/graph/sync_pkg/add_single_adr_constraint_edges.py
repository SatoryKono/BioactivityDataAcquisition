"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_adr_decision_node import _add_adr_decision_node
from memory.graph.sync_pkg.adr_title import (
    _doc_reference_context,
    _resolve_adr_constraint_target,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.normalize_docs_repo_reference import (
    _normalize_docs_repo_reference,
)

__all__ = [
    "_add_single_adr_constraint_edges",
]


def _add_single_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
    path_pattern: re.Pattern[str],
) -> None:
    relative_adr_path = _rel_path(root, adr_path)
    adr_node = _add_adr_decision_node(snapshot, root, project, today, adr_path)
    adr_doc = NodeKey("doc_artifact", relative_adr_path)
    if adr_doc in snapshot.nodes:
        snapshot.add_relation(
            adr_node, "DESCRIBED_IN", adr_doc, provenance="adr_constraints"
        )
    text = _read_text(adr_path)
    seen_targets: set[NodeKey] = set()
    for path_match in path_pattern.finditer(text):
        normalized = _normalize_docs_repo_reference(path_match.group(1))
        if normalized is None or normalized == relative_adr_path:
            continue
        target = _resolve_adr_constraint_target(snapshot, normalized)
        if target is None or target in seen_targets:
            continue
        seen_targets.add(target)
        section_title, section_anchor, line_number = _doc_reference_context(
            text, path_match.start()
        )
        snapshot.add_relation(
            adr_node,
            "CONSTRAINS",
            target,
            provenance="adr_path_reference",
            doc_reference=normalized,
            section_title=section_title,
            section_anchor=section_anchor,
            line_number=line_number,
            confidence="medium",
        )
