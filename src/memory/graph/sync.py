#!/usr/bin/env python3
"""Compatibility facade for deterministic graph sync entry points.

The implementation is split under ``memory.graph.sync_pkg`` so transport,
snapshot construction, apply, and CLI surfaces can be imported and tested
without loading this legacy all-in-one public module.
"""

from __future__ import annotations

from memory.graph.sync_pkg import *  # noqa: F403
from memory.graph.sync_pkg import __all__, main


if __name__ == "__main__":
    raise SystemExit(main())
