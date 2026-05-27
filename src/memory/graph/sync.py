#!/usr/bin/env python3
"""Compatibility facade for deterministic graph sync entry points.

The implementation is split under ``memory.graph.sync_pkg`` so transport,
snapshot construction, apply, and CLI surfaces can be imported and tested
without loading this legacy all-in-one public module.
"""

from __future__ import annotations

from memory.graph import sync_pkg as _sync_pkg
from memory.graph.sync_pkg import *  # noqa: F403

main = _sync_pkg.main
__all__ = list(_sync_pkg.__all__)


if __name__ == "__main__":
    raise SystemExit(main())
