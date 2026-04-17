#!/usr/bin/env python3
"""Compatibility shim for the packaged explicit docs link fixer."""

from __future__ import annotations

from importlib import import_module
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_IMPL = import_module("scripts.docs.fixers.fix_links_explicit")
globals().update(
    {
        name: value
        for name, value in vars(_IMPL).items()
        if name not in {"__name__", "__package__", "__loader__", "__spec__"}
    }
)


if __name__ == "__main__":
    raise SystemExit(main())
