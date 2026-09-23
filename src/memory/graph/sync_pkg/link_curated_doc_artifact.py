"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_summary_identifiers",
    "_add_summary_table_identifiers",
    "_evidence_summary_doc",
    "_link_curated_doc_artifact",
    "_summary_identifier_matches",
    "_summary_table_rows",
]


def _link_curated_doc_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    source_node: NodeKey,
    *,
    source_path: str,
    summary: str,
    today: str,
) -> None:
    path = root / source_path
    if not path.is_file():
        return
    artifact = snapshot.add_node(
        "doc_artifact",
        source_path,
        summary=summary,
        source_path=source_path,
        source_kind="doc_artifact",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(source_node, "BACKED_BY", artifact, provenance="curated_docs")


def _evidence_summary_doc(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    *,
    path: str,
    summary: str,
) -> tuple[Path, NodeKey]:
    doc_path = root / path
    relative_path = _rel_path(root, doc_path)
    doc = snapshot.add_node(
        "doc_artifact",
        relative_path,
        summary=summary,
        source_path=relative_path,
        source_kind="evidence_decision_summary",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    return doc_path, doc


def _summary_identifier_matches(path: Path, pattern: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(pattern, _read_text(path)))))


def _summary_table_rows(
    text: str, identifier_prefix: str
) -> tuple[tuple[str, str], ...]:
    pattern = re.compile(
        rf"\|\s*`({identifier_prefix}-[a-z0-9-]+)`\s*\|\s*([^|]+?)\s*\|",
        re.IGNORECASE,
    )
    return tuple(
        (match.group(1), match.group(2).strip()) for match in pattern.finditer(text)
    )


def _add_summary_identifiers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    doc: NodeKey,
    provenance: str,
    identifier_kind: str,
    matches: tuple[str, ...],
    summary: str,
    source_path: str,
) -> None:
    relation_type = "HAS_DECISION" if identifier_kind == "decision" else "HAS_RISK"
    for identifier in matches:
        node = snapshot.add_node(
            identifier_kind,
            identifier,
            summary=summary,
            source_path=source_path,
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(project, relation_type, node, provenance=provenance)
        snapshot.add_relation(node, "DESCRIBED_IN", doc, provenance=provenance)


def _add_summary_table_identifiers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    *,
    doc: NodeKey,
    provenance: str,
    identifier_kind: str,
    rows: tuple[tuple[str, str], ...],
    source_path: str,
) -> None:
    relation_type = "HAS_DECISION" if identifier_kind == "decision" else "HAS_RISK"
    for identifier, summary in rows:
        node = snapshot.add_node(
            identifier_kind,
            identifier,
            summary=summary,
            source_path=source_path,
            source_kind="evidence_decision_summary",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(project, relation_type, node, provenance=provenance)
        snapshot.add_relation(node, "DESCRIBED_IN", doc, provenance=provenance)
