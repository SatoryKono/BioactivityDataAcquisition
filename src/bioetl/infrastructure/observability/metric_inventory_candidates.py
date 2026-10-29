"""Invocation-local source candidates for the shared AST inventory scanner."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_discovery import (
    _iter_text_files,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _INFRASTRUCTURE_PATH_PREFIX,
    _RUNTIME_EXCLUDE_PARTS,
    _RUNTIME_SCAN_ROOT,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _read_runtime_candidate_text,
    _read_runtime_event_candidate_text,
)


def _iter_runtime_candidate_paths(repo_root: Path) -> list[Path]:
    return [
        path
        for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT)
        if path.suffix == ".py"
        and not any(part in path.as_posix() for part in _RUNTIME_EXCLUDE_PARTS)
        and _read_runtime_candidate_text(path) is not None
    ]


def _iter_runtime_event_candidate_paths(repo_root: Path) -> list[Path]:
    return [
        path
        for path in _iter_text_files(repo_root / _RUNTIME_SCAN_ROOT)
        if path.suffix == ".py"
        and _INFRASTRUCTURE_PATH_PREFIX not in path.as_posix()
        and _read_runtime_event_candidate_text(path) is not None
    ]


def _collect_runtime_candidate_texts(repo_root: Path) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for path in _iter_runtime_candidate_paths(repo_root):
        text = _read_runtime_candidate_text(path)
        if text is not None:
            candidates.append((path, text))
    return candidates
