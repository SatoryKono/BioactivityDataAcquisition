#!/usr/bin/env python3
"""Legacy compatibility entry point for ``python -m scripts.memory``."""

from __future__ import annotations

from memory.graph.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
