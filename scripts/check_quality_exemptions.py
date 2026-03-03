#!/usr/bin/env python3
"""Validate architecture metric exemption registry.

Gate behavior:
- metadata errors are always blocking
- expired exemptions are warning/blocking based on mode
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from bioetl.infrastructure.quality.exemptions_registry import (
    validate_exemptions_registry,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate quality exemption registry metadata and expiry."
    )
    parser.add_argument(
        "--registry",
        default="configs/quality/architecture_metric_exemptions.yaml",
        help="Path to exemptions registry YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=("warn", "block"),
        default=os.getenv("QUALITY_EXEMPTIONS_GATE_MODE", "warn").strip().lower(),
        help="Expiry gate mode: warn (non-blocking) or block (blocking).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    registry_path = Path(args.registry)

    metadata_errors, expired_entries = validate_exemptions_registry(registry_path)

    if metadata_errors:
        print("[quality-exemptions] metadata validation failed:")
        for item in metadata_errors:
            print(f"  - {item}")
        return 1

    if expired_entries:
        print(
            "[quality-exemptions] expired exemptions detected "
            f"(mode={args.mode}, count={len(expired_entries)}):"
        )
        for item in expired_entries:
            print(f"  - {item}")
        if args.mode == "block":
            return 1
        print("[quality-exemptions] WARNING mode enabled: not blocking this run.")

    print(
        "[quality-exemptions] registry validation passed "
        f"(mode={args.mode}, expired={len(expired_entries)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
