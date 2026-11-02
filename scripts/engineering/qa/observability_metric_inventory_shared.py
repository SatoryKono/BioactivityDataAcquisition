"""Compatibility facade for the canonical metric inventory shared module."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from bioetl.infrastructure.observability import (
    metric_inventory_shared as _metric_inventory_shared,
)

# Keep the historical engineering import path while sharing the implementation,
# caches, and patch seams with the runtime module.
sys.modules[__name__] = _metric_inventory_shared
