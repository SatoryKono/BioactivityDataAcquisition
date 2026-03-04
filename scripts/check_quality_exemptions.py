#!/usr/bin/env python3
"""Validate architecture metric exemption registry and debt scorecard.

Gate behavior:
- metadata errors are always blocking
- expired exemptions are warning/blocking based on mode
- budget growth violations are warning/blocking based on growth mode
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from bioetl.infrastructure.quality.debt_scorecard import (
    evaluate_debt_scorecard,
    validate_debt_scorecard,
)
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
        "--scorecard",
        default=os.getenv("QUALITY_EXEMPTIONS_SCORECARD", "configs/quality/debt_scorecard.yaml"),
        help="Path to debt scorecard YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=("warn", "block"),
        default=os.getenv("QUALITY_EXEMPTIONS_GATE_MODE", "warn").strip().lower(),
        help="Expiry gate mode: warn (non-blocking) or block (blocking).",
    )
    parser.add_argument(
        "--growth-mode",
        choices=("warn", "block"),
        default=os.getenv("QUALITY_EXEMPTIONS_GROWTH_MODE", "block").strip().lower(),
        help="Growth/budget gate mode: warn (non-blocking) or block (blocking).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    registry_path = Path(args.registry)
    scorecard_path = Path(args.scorecard)

    metadata_errors, expired_entries = validate_exemptions_registry(registry_path)
    scorecard_errors = validate_debt_scorecard(scorecard_path)
    growth_violations, summary = evaluate_debt_scorecard(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
    )

    if metadata_errors:
        print("[quality-exemptions] metadata validation failed:")
        for item in metadata_errors:
            print(f"  - {item}")
        return 1

    if scorecard_errors:
        print("[quality-exemptions] scorecard validation failed:")
        for item in scorecard_errors:
            print(f"  - {item}")
        return 1

    if summary is None:
        print("[quality-exemptions] scorecard evaluation failed: no summary")
        return 1

    print(
        "[quality-exemptions] scorecard snapshot "
        f"(quarter={summary.quarter}, score={summary.integral_score}, "
        f"total={summary.total_exemptions}/{summary.total_budget})"
    )
    print("[quality-exemptions] breakdown by registry:")
    for registry_name, count in summary.by_registry.items():
        print(f"  - {registry_name}: {count}")
    print("[quality-exemptions] breakdown by owner:")
    for owner, count in summary.by_owner.items():
        print(f"  - {owner}: {count}")
    print("[quality-exemptions] breakdown by expiry quarter:")
    for quarter, count in summary.by_expiry_quarter.items():
        print(f"  - {quarter}: {count}")
    if summary.active_grace_windows:
        print(
            "[quality-exemptions] active grace windows: "
            + ", ".join(summary.active_grace_windows)
        )

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

    if growth_violations:
        print(
            "[quality-exemptions] budget growth violations detected "
            f"(growth-mode={args.growth_mode}, count={len(growth_violations)}):"
        )
        for item in growth_violations:
            print(f"  - {item}")
        if args.growth_mode == "block":
            return 1
        print("[quality-exemptions] WARNING mode enabled: not blocking growth violations.")

    print(
        "[quality-exemptions] registry validation passed "
        "(expiry-mode="
        f"{args.mode}, growth-mode={args.growth_mode}, expired={len(expired_entries)}, "
        f"violations={len(growth_violations)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
