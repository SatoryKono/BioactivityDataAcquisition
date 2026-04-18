#!/usr/bin/env python3
"""Shared path helpers for BioETL scripts.

This module provides common path resolution utilities to avoid duplication
across scripts.
"""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve the repository root directory.
    
    Returns:
        Path: The repository root directory.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = resolve_repo_root()
