"""Compatibility wrapper for architecture dependency map generation.

Canonical implementation lives in scripts/engineering/qa/generate_architecture_dependency_map.py.
This wrapper preserves historical invocation paths used by docs and tooling.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path


def _load_main() -> Callable[[], int]:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from scripts.engineering.qa.generate_architecture_dependency_map import main

    return main


if __name__ == "__main__":
    raise SystemExit(_load_main()())
