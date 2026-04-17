"""Compatibility wrapper for scripts catalog governance checks.

Canonical implementation lives in scripts/engineering/repo/check_scripts_catalog.py.
This wrapper preserves historical import paths used by architecture tests and tooling.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path


def _load_main() -> Callable[[list[str] | None], int]:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.engineering.repo.check_scripts_catalog import main

    return main


def main(argv: list[str] | None = None) -> int:
    """Delegate to the canonical scripts catalog governance checker."""
    return _load_main()(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
