#!/usr/bin/env python3
"""Compatibility shim for the packaged documentation link checker."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_SHIM_FILE = __file__
_SHIM_PACKAGE = __package__
_IMPL_FILE = Path(__file__).resolve().parent / "checks" / "check_links.py"

globals()["__file__"] = str(_IMPL_FILE)
globals()["__package__"] = "scripts.docs.checks"
exec(compile(_IMPL_FILE.read_text(encoding="utf-8"), str(_IMPL_FILE), "exec"), globals())
globals()["__file__"] = _SHIM_FILE
globals()["__package__"] = _SHIM_PACKAGE


if __name__ == "__main__":
    raise SystemExit(main())
