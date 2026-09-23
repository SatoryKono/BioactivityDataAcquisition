"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _normalize_cli_command_name, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_doc_describes_relation import _add_doc_describes_relation
from memory.graph.sync_pkg.adr_title import _adr_title
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.markdown_headings import _resolve_docs_reference_target
from memory.graph.sync_pkg.normalize_docs_repo_reference import (
    _normalize_docs_repo_reference,
)

__all__ = [
    "_add_adr_decision_node",
    "_add_doc_command_reference_edges",
    "_add_doc_path_reference_edges",
]


def _add_adr_decision_node(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    adr_path: Path,
) -> NodeKey:
    relative_adr_path = _rel_path(root, adr_path)
    title = _adr_title(adr_path)
    adr_node = snapshot.add_node(
        "decision",
        adr_path.stem,
        summary=title,
        source_path=relative_adr_path,
        source_kind="adr",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_DECISION", adr_node, provenance="adr")
    return adr_node


def _add_doc_path_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    path_pattern: re.Pattern[str],
) -> None:
    seen_matches: set[tuple[str, str]] = set()
    for path_match in path_pattern.finditer(text):
        match = path_match.group(1)
        normalized = _normalize_docs_repo_reference(match)
        if normalized is None:
            continue
        target, evidence_kind, confidence = _resolve_docs_reference_target(
            snapshot, normalized
        )
        if target is None or target == source_node:
            continue
        dedupe_key = (normalized, target.name)
        if dedupe_key in seen_matches:
            continue
        seen_matches.add(dedupe_key)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            target,
            text,
            path_match.start(),
            doc_reference=normalized,
            evidence_kind=evidence_kind,
            confidence=confidence,
        )


def _add_doc_command_reference_edges(
    snapshot: GraphSnapshot,
    source_node: NodeKey,
    text: str,
    command_pattern: re.Pattern[str],
) -> None:
    seen_commands: set[str] = set()
    for command_match in command_pattern.finditer(text):
        raw_command = command_match.group(0).strip()
        command_name = _normalize_cli_command_name(raw_command)
        if command_name is None or command_name in seen_commands:
            continue
        command_key = NodeKey("cli_command_surface", command_name)
        if command_key not in snapshot.nodes:
            continue
        seen_commands.add(command_name)
        _add_doc_describes_relation(
            snapshot,
            source_node,
            command_key,
            text,
            command_match.start(),
            doc_reference=raw_command,
            evidence_kind="command_reference",
            confidence="medium",
        )
