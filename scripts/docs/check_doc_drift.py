#!/usr/bin/env python3
"""Compatibility shim for the packaged documentation drift entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.docs.checks.check_drift import main

if __name__ == "__main__":
    raise SystemExit(main())
