"""Repo-root compatibility shim for the canonical ``src/memory`` package."""

from __future__ import annotations

from pathlib import Path

_SRC_MEMORY = Path(__file__).resolve().parents[1] / "src" / "memory"

if not _SRC_MEMORY.is_dir():  # pragma: no cover - defensive bootstrap guard
    raise ModuleNotFoundError(
        f"Canonical memory package directory is missing: {_SRC_MEMORY}"
    )

# Point package submodule discovery at the canonical src-layout implementation.
__path__ = [str(_SRC_MEMORY)]
__all__ = ["query", "resources", "validation"]
