"""Filesystem discovery for installed diagnostics, without engineering executables."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_shared import (
    _CANONICAL_METRIC_RE,
    _TEXT_SUFFIXES,
)
from bioetl.infrastructure.observability.metric_inventory_text import (
    _normalize_mapping_lists,
)


def _iter_text_files(root: Path) -> list[Path]:
    """Enumerate the explicit input root without Git, rg, or a source checkout."""
    if root.is_file():
        return [root] if root.suffix in _TEXT_SUFFIXES else []
    paths: list[Path] = []
    for directory, _, names in os.walk(root):
        paths.extend(
            Path(directory) / name
            for name in names
            if Path(name).suffix in _TEXT_SUFFIXES
        )
    return sorted(paths)


def _scan_canonical_metric_mentions(
    paths: list[Path], repo_root: Path
) -> dict[str, list[str]]:
    return _scan_canonical_metric_mentions_via_direct_reads(paths, repo_root)


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_canonical_metric_mentions_via_direct_reads(
    paths: list[Path],
    repo_root: Path,
) -> dict[str, list[str]]:
    mentions: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")  # NOSONAR - path confined
        except (OSError, UnicodeDecodeError):
            continue
        for metric_name in sorted(set(_CANONICAL_METRIC_RE.findall(text))):
            mentions[metric_name].append(_as_repo_relative(path, repo_root))
    return _normalize_mapping_lists(mentions)
