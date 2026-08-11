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
    DEFAULT_FIXTURE_DUPLICATION_ARTIFACT,
    DEFAULT_JSON_ARTIFACT,
    collect_test_governance_report,
    evaluate_budgets,
    load_config,
)


def _canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _check_json_artifact(path: Path, payload: dict[str, object]) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[drift] unreadable: {path}: {exc}")
        return False
    if actual == _canonical_json(payload):
        return True
    print(f"[drift] mismatch: {path}")
    return False


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
        default=None,
        help=(
            "Optional path to write a duplicate-name inventory JSON. The committed "
            "baseline keeps this inventory embedded in the main governance artifact."
        ),
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
    from scripts.engineering.common.repo_paths import resolve_output_path

    args = _parse_args()

    config_path = resolve_output_path(args.config)
    root = config_path.resolve().parents[2]
    output_path = resolve_output_path(args.output, root=root)
    duplicate_name_path = (
        resolve_output_path(args.duplicate_name_inventory, root=root)
        if args.duplicate_name_inventory
        else None
    )
    fixture_duplication_path = resolve_output_path(args.fixture_duplication, root=root)

    if args.verbose:
        print(f"Root: {root}")
        print(f"Config: {config_path}")
        print(f"Output: {output_path}")
        print(f"Duplicate name inventory: {duplicate_name_path or '<embedded-only>'}")
        print(f"Fixture duplication: {fixture_duplication_path}")

    # Collect the report (this is the expensive operation)
    payload = collect_test_governance_report(root)
    if config_path.exists():
        payload["budget_violations"] = evaluate_budgets(
            payload["report"],
            load_config(config_path),
        )

    # Write or verify the main artifact.
    if not args.check:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_canonical_json(payload), encoding="utf-8")

    # Write duplicate name inventory
    duplicate_inventory_payload = {
        "summary": payload["report"]["duplicate_test_name_inventory_summary"],
        "inventory": payload["report"]["duplicate_test_name_inventory"],
    }
    if not args.check and duplicate_name_path is not None:
        duplicate_name_path.parent.mkdir(parents=True, exist_ok=True)
        duplicate_name_path.write_text(
            json.dumps(duplicate_inventory_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # Write fixture duplication inventory
    fixture_duplication_payload = payload["report"]["fixture_asset_duplication"]
    if args.check:
        checks = [
            _check_json_artifact(output_path, payload),
            _check_json_artifact(
                fixture_duplication_path,
                fixture_duplication_payload,
            ),
        ]
        if duplicate_name_path is not None:
            checks.append(
                _check_json_artifact(
                    duplicate_name_path,
                    duplicate_inventory_payload,
                )
            )
        return 0 if all(checks) else 1

    if not args.check:
        fixture_duplication_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_duplication_path.write_text(
            _canonical_json(fixture_duplication_payload), encoding="utf-8"
        )

    if args.verbose:
        print(f"Report collected with {len(payload.get('report', {}))} sections")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
