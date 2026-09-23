"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_adr_decision_node import (
    _add_doc_command_reference_edges,
    _add_doc_path_reference_edges,
)
from memory.graph.sync_pkg.add_doc_claim_edges import _add_doc_claim_edges
from memory.graph.sync_pkg.add_single_adr_constraint_edges import (
    _add_single_adr_constraint_edges,
)
from memory.graph.sync_pkg.adr_constraint_candidates import (
    _docs_command_pattern,
    _docs_drift_sources,
    _docs_path_pattern,
)
from memory.graph.sync_pkg.default_batch_size import ADR_DECISIONS_DIR
from memory.graph.sync_pkg.file_structure import _file_structure_config
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _load_memory_mapping

__all__ = [
    "_add_adr_constraint_edges",
    "_add_docs_to_code_drift_edges",
]


def _add_docs_to_code_drift_edges(snapshot: GraphSnapshot, root: Path) -> None:
    path_pattern = _docs_path_pattern()
    command_pattern = _docs_command_pattern()
    config = _file_structure_config(_load_memory_mapping(root))
    for source_node, source_path, text in _docs_drift_sources(snapshot, root, config):
        _add_doc_path_reference_edges(snapshot, source_node, text, path_pattern)
        _add_doc_command_reference_edges(snapshot, source_node, text, command_pattern)
        _add_doc_claim_edges(snapshot, source_node, source_path, text, path_pattern)


def _add_adr_constraint_edges(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    decisions_dir = root / ADR_DECISIONS_DIR
    if not decisions_dir.is_dir():
        return
    path_pattern = _docs_path_pattern()
    for adr_path in sorted(decisions_dir.glob("ADR-*.md")):
        _add_single_adr_constraint_edges(
            snapshot,
            root,
            project,
            today,
            adr_path,
            path_pattern,
        )
