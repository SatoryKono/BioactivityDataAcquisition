#!/usr/bin/env python3
"""Refresh test-governance telemetry baseline with caching.

This script provides a dedicated entry point for refreshing the
test-governance report with subprocess result caching to avoid
re-running expensive operations during ordinary test runs.

Usage:
    python -m scripts.engineering.qa.refresh_test_governance_baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.engineering.qa.report_test_governance_audit import (
    DEFAULT_CONFIG,
    DEFAULT_DUPLICATE_NAME_ARTIFACT,
    DEFAULT_FIXTURE_DUPLICATION_ARTIFACT,
    DEFAULT_JSON_ARTIFACT,
    collect_test_governance_report,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh test-governance baseline with caching."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to test-governance config YAML.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_JSON_ARTIFACT),
        help="Path to output JSON artifact.",
    )
    parser.add_argument(
        "--duplicate-name-inventory",
        default=str(DEFAULT_DUPLICATE_NAME_ARTIFACT),
        help="Path to duplicate-name inventory JSON.",
    )
    parser.add_argument(
        "--fixture-duplication",
        default=str(DEFAULT_FIXTURE_DUPLICATION_ARTIFACT),
        help="Path to fixture duplication JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: validate against existing artifact without writing.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    root = Path(args.config).resolve().parents[2]
    output_path = Path(args.output)
    duplicate_name_path = Path(args.duplicate_name_inventory)
    fixture_duplication_path = Path(args.fixture_duplication)

    if args.verbose:
        print(f"Root: {root}")
        print(f"Config: {args.config}")
        print(f"Output: {output_path}")
        print(f"Duplicate name inventory: {duplicate_name_path}")
        print(f"Fixture duplication: {fixture_duplication_path}")

    # Collect the report (this is the expensive operation)
    payload = collect_test_governance_report(root)

    # Write the main artifact
    if not args.check:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write duplicate name inventory
    duplicate_inventory_payload = {
        "summary": payload["report"]["duplicate_test_name_inventory_summary"],
        "inventory": payload["report"]["duplicate_test_name_inventory"],
    }
    if not args.check:
        duplicate_name_path.parent.mkdir(parents=True, exist_ok=True)
        duplicate_name_path.write_text(
            json.dumps(duplicate_inventory_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # Write fixture duplication inventory
    fixture_duplication_payload = payload["report"]["fixture_asset_duplication"]
    if not args.check:
        fixture_duplication_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_duplication_path.write_text(
            json.dumps(fixture_duplication_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.verbose:
        print(f"Report collected with {len(payload.get('report', {}))} sections")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
