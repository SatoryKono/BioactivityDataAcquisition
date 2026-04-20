#!/usr/bin/env python3
"""Compatibility shim for the packaged docs KPI entrypoint."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _compat_shim import load_main
else:
    from ._compat_shim import load_main

main = load_main("scripts.docs.checks.report_docs_kpi")

if __name__ == "__main__":
    raise SystemExit(main())
