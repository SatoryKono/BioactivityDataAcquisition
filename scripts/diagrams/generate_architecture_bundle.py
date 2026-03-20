#!/usr/bin/env python3
"""Compatibility wrapper for the canonical diagram bundle generator.

Canonical script:
- scripts/diagrams/generate_all_bundles.py --collection architecture
"""

from __future__ import annotations

try:
    from .generate_all_bundles import main as canonical_main
except ImportError:  # pragma: no cover - direct script execution
    from generate_all_bundles import main as canonical_main


if __name__ == "__main__":
    raise SystemExit(canonical_main(["--collection", "architecture"]))
