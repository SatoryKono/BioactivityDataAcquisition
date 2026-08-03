#!/usr/bin/env python3
"""Compatibility shim for the packaged documentation drift entrypoint."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts.docs._compat_shim import load_public_api
else:
    from ._compat_shim import load_public_api

_IMPL = load_public_api(globals(), "scripts.docs.checks.check_drift")
main = _IMPL.main
DriftReport = _IMPL.DriftReport
check_freshness = _IMPL.check_freshness
check_runtime_mirrors = _IMPL.check_runtime_mirrors

__all__ = [
    "DriftReport",
    "check_freshness",
    "check_runtime_mirrors",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())
