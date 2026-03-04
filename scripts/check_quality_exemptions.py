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
from datetime import date
from pathlib import Path

from bioetl.infrastructure.quality.debt_scorecard import (
    evaluate_debt_scorecard,
    load_debt_scorecard,
    split_growth_violations_by_severity,
    validate_debt_scorecard,
    validate_scorecard_registry_sync,
)
from bioetl.infrastructure.quality.exemptions_registry import (
    load_exemptions_registry,
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
        default=os.getenv(
            "QUALITY_EXEMPTIONS_SCORECARD", "configs/quality/debt_scorecard.yaml"
        ),
        help="Path to debt scorecard YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=("warn", "block", "auto"),
        default=os.getenv("QUALITY_EXEMPTIONS_GATE_MODE", "auto").strip().lower(),
        help="Expiry gate mode: warn (non-blocking) or block (blocking).",
    )
    parser.add_argument(
        "--growth-mode",
        choices=("warn", "block", "auto"),
        default=os.getenv("QUALITY_EXEMPTIONS_GROWTH_MODE", "auto").strip().lower(),
        help="Growth/budget gate mode: warn (non-blocking) or block (blocking).",
    )
    return parser.parse_args()


def _resolve_expiry_mode(
    *,
    requested_mode: str,
    registry_raw: dict[str, object],
    today: date,
) -> str:
    if requested_mode in {"warn", "block"}:
        return requested_mode

    policy = registry_raw.get("policy", {})
    if not isinstance(policy, dict):
        return "block"

    warning_mode_until = policy.get("warning_mode_until")
    if isinstance(warning_mode_until, str):
        try:
            warning_until_date = date.fromisoformat(warning_mode_until)
        except ValueError:
            warning_until_date = None
        if warning_until_date is not None and today <= warning_until_date:
            return "warn"

    default_gate_mode = policy.get("default_gate_mode")
    if isinstance(default_gate_mode, str):
        normalized = default_gate_mode.strip().lower()
        if normalized in {"warn", "block"}:
            return normalized
    return "block"


def _resolve_growth_mode(
    *,
    requested_mode: str,
    scorecard_raw: dict[str, object],
) -> str:
    if requested_mode in {"warn", "block"}:
        return requested_mode

    governance = scorecard_raw.get("governance", {})
    if not isinstance(governance, dict):
        return "block"

    default_mode = governance.get("growth_gate_default_mode")
    if isinstance(default_mode, str):
        normalized = default_mode.strip().lower()
        if normalized in {"warn", "block"}:
            return normalized
    return "block"


def main() -> int:
    args = _parse_args()
    today = date.today()
    registry_path = Path(args.registry)
    scorecard_path = Path(args.scorecard)
    registry_raw = load_exemptions_registry(registry_path)
    scorecard_raw = load_debt_scorecard(scorecard_path)

    expiry_mode = _resolve_expiry_mode(
        requested_mode=args.mode,
        registry_raw=registry_raw,
        today=today,
    )
    growth_mode = _resolve_growth_mode(
        requested_mode=args.growth_mode,
        scorecard_raw=scorecard_raw,
    )

    metadata_errors, expired_entries = validate_exemptions_registry(
        registry_path,
        today=today,
    )
    scorecard_errors = validate_debt_scorecard(scorecard_path)
    sync_errors = validate_scorecard_registry_sync(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
        today=today,
    )
    growth_violations, summary = evaluate_debt_scorecard(
        registry_path=registry_path,
        scorecard_path=scorecard_path,
        today=today,
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

    if sync_errors:
        print("[quality-exemptions] scorecard/registry sync validation failed:")
        for item in sync_errors:
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
            f"(mode={expiry_mode}, count={len(expired_entries)}):"
        )
        for item in expired_entries:
            print(f"  - {item}")
        if expiry_mode == "block":
            return 1
        print("[quality-exemptions] WARNING mode enabled: not blocking this run.")

    if growth_violations:
        blocking_growth, warning_growth = split_growth_violations_by_severity(
            violations=growth_violations,
            scorecard=scorecard_raw,
            today=today,
            fallback_mode=growth_mode,
        )
        if warning_growth:
            print(
                "[quality-exemptions] budget growth warnings detected "
                f"(growth-mode={growth_mode}, count={len(warning_growth)}):"
            )
            for item in warning_growth:
                print(f"  - {item}")
            print(
                "[quality-exemptions] WARNING mode enabled by staged rollout "
                "for listed sections."
            )
        if blocking_growth:
            print(
                "[quality-exemptions] budget growth violations detected "
                f"(growth-mode={growth_mode}, count={len(blocking_growth)}):"
            )
            for item in blocking_growth:
                print(f"  - {item}")
            return 1
    print(
        "[quality-exemptions] registry validation passed "
        "(expiry-mode="
        f"{expiry_mode}, growth-mode={growth_mode}, expired={len(expired_entries)}, "
        f"violations={len(growth_violations)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
