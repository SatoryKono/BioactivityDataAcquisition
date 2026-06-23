#!/usr/bin/env python3
"""Compatibility module alias for the canonical ``memory.graph.query`` surface."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_impl = importlib.import_module("memory.graph.query")

main = _impl.main
globals().update(
    {name: value for name, value in vars(_impl).items() if name != "__name__"}
)
__all__ = [name for name in vars(_impl) if not name.startswith("__")]
sys.modules[__name__] = _impl

if __name__ == "__main__":
    raise SystemExit(main())
