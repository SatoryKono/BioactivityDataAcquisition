"""Compatibility wrapper for Grafana screenshot rerendering.

Canonical implementation lives in scripts/ops/rerender_grafana_screenshots.py.
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
    from scripts.ops.rerender_grafana_screenshots import main

    return main


if __name__ == "__main__":
    raise SystemExit(_load_main()())
