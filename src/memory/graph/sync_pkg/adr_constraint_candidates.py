"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _is_excluded_docs_drift_prefix,
    _read_text,
)
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOC_LIKE_LABELS,
    _DOCS_DRIFT_TEXT_EXTENSIONS,
    _is_docs_drift_source_candidate,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import (
    _coerce_repo_relative_path,
    _is_excluded_file_structure_path,
)

__all__ = [
    "_adr_constraint_candidates",
    "_docs_command_pattern",
    "_docs_drift_sources",
    "_docs_path_pattern",
    "_normalize_docs_drift_source_path",
    "_read_docs_drift_text",
]


def _adr_constraint_candidates(normalized_ref: str) -> tuple[NodeKey, ...]:
    return (
        NodeKey("module_surface", normalized_ref),
        NodeKey("config_artifact", normalized_ref),
        NodeKey("test_artifact", normalized_ref),
        NodeKey("file_surface", normalized_ref),
        NodeKey("directory_surface", normalized_ref),
    )


def _docs_path_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?<![\w./-])("
        r"README\.md|mkdocs\.yml|\.github/[\w./*-]+|"
        r"(?:src|configs|scripts|tests|docs|grafana)/[\w./*-]+"
        r")"
    )


def _docs_command_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?:python3?\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*|"
        r"uv\s+run\s+python3?\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*|"
        r"uv\s+run\s+python\s+-m\s+(?:bioetl|scripts\.\w+)(?:\s+[\w.-]+)?(?:\s+--?[\w][\w-]*(?:[ =][^\s`]+)?)*"
        r")"
    )


def _normalize_docs_drift_source_path(
    root: Path,
    source_path: object,
    config: dict[str, object],
) -> str | None:
    if not isinstance(source_path, str):
        return None
    normalized_source_path = _coerce_repo_relative_path(root, source_path)
    if not normalized_source_path:
        return None
    if _is_excluded_docs_drift_prefix(normalized_source_path):
        return None
    if _is_excluded_file_structure_path(normalized_source_path, config):
        return None
    if Path(normalized_source_path).suffix.lower() not in _DOCS_DRIFT_TEXT_EXTENSIONS:
        return None
    return normalized_source_path


def _read_docs_drift_text(
    root: Path,
    normalized_source_path: str,
    cached_text: dict[str, str],
) -> str | None:
    text = cached_text.get(normalized_source_path)
    if text is not None:
        return text
    try:
        text = _read_text(root / normalized_source_path)
    except OSError:
        # Some tracked doc paths can exist in the graph but still be
        # unreadable on a given checkout or platform mount. Skip them
        # instead of failing the entire snapshot build.
        return None
    cached_text[normalized_source_path] = text
    return text


def _docs_drift_sources(
    snapshot: GraphSnapshot,
    root: Path,
    config: dict[str, object],
) -> Iterator[tuple[NodeKey, str, str]]:
    cached_text: dict[str, str] = {}
    for node in tuple(snapshot.nodes.values()):
        if node.key.label not in _DOC_LIKE_LABELS:
            continue
        if not _is_docs_drift_source_candidate(node):
            continue
        normalized_source_path = _normalize_docs_drift_source_path(
            root,
            node.properties.get("source_path"),
            config,
        )
        if normalized_source_path is None:
            continue
        text = _read_docs_drift_text(root, normalized_source_path, cached_text)
        if text is None:
            continue
        yield node.key, normalized_source_path, text
