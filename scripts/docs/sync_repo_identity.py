#!/usr/bin/env python3
"""Compatibility shim for the packaged repo identity fixer."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.docs.fixers.repo_identity import main


if __name__ == "__main__":
    raise SystemExit(main())
