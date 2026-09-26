#!/usr/bin/env python3
"""Consolidated bootstrap helpers for scripts.docs modules."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.engineering.common.repo_paths import REPO_ROOT

PROJECT_ROOT = REPO_ROOT
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_repo_imports(*, include_src: bool = False) -> None:
    """Ensure repo-local packages are importable for direct script execution."""
    search_paths = [PROJECT_ROOT]
    if include_src:
        search_paths.append(PROJECT_ROOT / "src")
    for path in reversed(search_paths):
        resolved = str(path)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)
