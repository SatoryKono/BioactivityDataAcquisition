#!/usr/bin/env python3
"""Shared filesystem discovery helpers for QA inventory/report scripts."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

__all__ = ["discover_files"]

_PRUNED_DIR_NAMES = frozenset(
    {
        ".cache",
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".venv-win",
        "__pycache__",
        "htmlcov",
        "node_modules",
    }
)
_PRUNED_RELATIVE_PREFIXES = (
    "tests/fixtures/",
    "tests/snapshots/",
)


def _should_prune(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in _PRUNED_RELATIVE_PREFIXES)


@lru_cache(maxsize=None)
def discover_files(
    root_str: str,
    suffix: str,
    filename_prefix: str = "",
) -> tuple[str, ...]:
    """Return a stable file inventory for one rooted subtree."""
    root = Path(root_str)
    if not root.exists():
        return ()

    discovered: list[str] = []
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        relative_root = current_path.relative_to(root).as_posix()
        relative_prefix = "" if relative_root == "." else f"{relative_root}/"

        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in _PRUNED_DIR_NAMES
            and not _should_prune(f"{relative_prefix}{dirname}/")
        )
        if relative_root != "." and _should_prune(f"{relative_root}/"):
            dirnames[:] = []
            continue

        for filename in sorted(filenames):
            if filename_prefix and not filename.startswith(filename_prefix):
                continue
            if not filename.endswith(suffix):
                continue
            discovered.append(f"{relative_prefix}{filename}")

    return tuple(discovered)
