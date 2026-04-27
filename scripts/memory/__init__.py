"""Legacy compatibility package for canonical ``memory.*`` surfaces."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_MEMORY = _REPO_ROOT / "src" / "memory"

# Expose canonical src/memory subpackages (graph, tooling, notes, ...) when
# this compatibility package is imported as top-level ``memory``.
if _SRC_MEMORY.is_dir():
    __path__.append(str(_SRC_MEMORY))  # type: ignore[name-defined]
