#!/usr/bin/env python3
"""Compatibility module alias for the canonical ``memory.graph.query`` surface."""

from __future__ import annotations

import sys

from memory.graph import query as _impl

if __name__ == "__main__":
    raise SystemExit(_impl.main())

sys.modules[__name__] = _impl
