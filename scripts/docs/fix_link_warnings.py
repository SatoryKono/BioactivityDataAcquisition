#!/usr/bin/env python3
"""Compatibility shim for the packaged Mermaid link warning fixer."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _compat_shim import load_public_api
else:
    from ._compat_shim import load_public_api

_IMPL = load_public_api(globals(), "scripts.docs.fixers.link_warnings")
main = _IMPL.main


if __name__ == "__main__":
    raise SystemExit(main())
