#!/usr/bin/env python3
"""Compatibility wrapper for the canonical pipeline config validator.

Canonical script:
- scripts/schema/validate_pipeline_configs.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    """Run the canonical validator without making this docs path canonical."""
    validator = importlib.import_module("scripts.schema.validate_pipeline_configs")
    return int(validator.main())


if __name__ == "__main__":
    raise SystemExit(main())
