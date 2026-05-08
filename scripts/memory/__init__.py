"""Legacy compatibility package for canonical ``memory.*`` surfaces."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_MEMORY = _REPO_ROOT / "src" / "memory"

# Expose canonical src/memory subpackages (graph, tooling, notes, ...) when
# this compatibility package is imported as top-level ``memory``.
if _SRC_MEMORY.is_dir():
    _src_memory_path = str(_SRC_MEMORY)
    if _src_memory_path not in __path__:  # type: ignore[name-defined]
        if __name__ == "memory":
            __path__.insert(0, _src_memory_path)  # type: ignore[name-defined]
        else:
            __path__.append(_src_memory_path)  # type: ignore[name-defined]
