"""Compatibility wrapper for architecture dependency map generation.

Canonical implementation lives in scripts/qa/generate_architecture_dependency_map.py.
This wrapper preserves historical invocation paths used by docs and tooling.
"""

from __future__ import annotations

from scripts.qa.generate_architecture_dependency_map import main


if __name__ == "__main__":
    raise SystemExit(main())
