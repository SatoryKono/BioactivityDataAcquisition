"""Memory management tools for AI systems."""

from __future__ import annotations

from pathlib import Path

# Keep legacy compatibility for canonical src/memory surfaces
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_MEMORY = _REPO_ROOT / "src" / "memory"

if _SRC_MEMORY.is_dir():
    _src_memory_path = str(_SRC_MEMORY)
    if _src_memory_path not in __path__:  # type: ignore[name-defined]
        if __name__ == "memory":
            __path__.insert(0, _src_memory_path)  # type: ignore[name-defined]
        else:
            __path__.append(_src_memory_path)  # type: ignore[name-defined]

# Export new structured subsystem
try:
    from scripts.memory.queries import query
    from scripts.memory.operations import sync

    __all__ = [
        "query",
        "sync",
    ]
except ImportError:
    # If src/memory is not available, just export empty __all__
    __all__ = []
