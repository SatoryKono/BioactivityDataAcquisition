"""Shared platform skip helpers for mounted-worktree architecture tests."""

from __future__ import annotations

import sys


def mounted_worktree_skip_reason() -> str | None:
    """Return the canonical skip reason for Windows-backed slow filesystem lanes."""
    if sys.platform.startswith("win"):
        return "Skipped on Windows due to filesystem performance"

    try:
        with open("/proc/version", encoding="utf-8") as handle:
            if "microsoft" in handle.read().lower():
                return "Skipped on WSL due to filesystem performance"
    except OSError:
        return None

    return None
