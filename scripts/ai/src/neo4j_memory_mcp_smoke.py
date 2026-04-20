#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.src.neo4j_memory_mcp_smoke`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.ai.mcp.neo4j_memory_mcp_smoke as _impl

main = _impl.main
__all__ = getattr(_impl, "__all__", [name for name in vars(_impl) if not name.startswith("_")])
globals().update({name: getattr(_impl, name) for name in __all__})


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
