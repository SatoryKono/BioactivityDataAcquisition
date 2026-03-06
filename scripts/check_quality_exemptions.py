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

from bioetl.infrastructure.quality._primitives import _parse_quarter_label
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
    parser.add_argument(
        "--temp-window-mode",
        choices=("off", "budget-only", "auto"),
        default=os.getenv("QUALITY_EXEMPTIONS_TEMP_WINDOW_MODE", "auto")
        .strip()
        .lower(),
        help=(
            "Temporary grace-window policy: off, budget-only, or auto "
            "(resolved from scorecard governance)."
        ),
    )
    parser.add_argument(
        "--max-grace-window-days",
        type=int,
        default=int(os.getenv("QUALITY_EXEMPTIONS_MAX_GRACE_WINDOW_DAYS", "45")),
        help=(
            "Fallback max duration for active grace windows when temp-window "
            "policy is budget-only."
        ),
    )
    parser.add_argument(
        "--trend-report",
        choices=("on", "off"),
        default=os.getenv("QUALITY_EXEMPTIONS_TREND_REPORT", "on").strip().lower(),
        help=("Print burn-down trend report for priority registries (default: on)."),
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


def _resolve_temp_window_mode(
    *,
    requested_mode: str,
    scorecard_raw: dict[str, object],
) -> str:
    if requested_mode in {"off", "budget-only"}:
        return requested_mode

    governance = scorecard_raw.get("governance", {})
    if not isinstance(governance, dict):
        return "budget-only"

    temporary = governance.get("temporary_exemptions", {})
    if not isinstance(temporary, dict):
        return "budget-only"

    policy = temporary.get("window_policy", temporary.get("mode"))
    if isinstance(policy, str):
        normalized = policy.strip().lower()
        if normalized in {"off", "budget-only"}:
            return normalized
    return "budget-only"


def _resolve_max_grace_window_days(
    *,
    scorecard_raw: dict[str, object],
    fallback_days: int,
) -> int:
    governance = scorecard_raw.get("governance", {})
    if not isinstance(governance, dict):
        return fallback_days

    temporary = governance.get("temporary_exemptions", {})
    if not isinstance(temporary, dict):
        return fallback_days

    configured = temporary.get("max_window_days")
    if isinstance(configured, int) and configured > 0:
        return configured
    return fallback_days


def _parse_iso_date(raw_value: object) -> date | None:
    if not isinstance(raw_value, str):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _validate_budget_only_grace_windows(
    *,
    scorecard_raw: dict[str, object],
    today: date,
    max_window_days: int,
) -> list[str]:
    governance_errors: list[str] = []
    grace_windows = scorecard_raw.get("grace_windows", [])
    if not isinstance(grace_windows, list):
        return ["grace_windows: expected list"]

    allowed_window_keys = {
        "rf_id",
        "approved",
        "starts_on",
        "ends_on",
        "allowances",
        "note",
    }
    allowed_allowance_keys = {
        "total_exemptions",
        "registry_budgets",
        "group_budgets",
    }

    for index, window in enumerate(grace_windows):
        if not isinstance(window, dict):
            continue
        if not window.get("approved"):
            continue

        starts_on = _parse_iso_date(window.get("starts_on"))
        ends_on = _parse_iso_date(window.get("ends_on"))
        if starts_on is None or ends_on is None:
            continue
        if not (starts_on <= today <= ends_on):
            continue

        window_prefix = f"grace_windows[{index}]"
        unknown_window_keys = sorted(set(window) - allowed_window_keys)
        if unknown_window_keys:
            governance_errors.append(
                f"{window_prefix}: non-budget keys are not allowed in budget-only mode: "
                f"{unknown_window_keys}"
            )

        duration_days = (ends_on - starts_on).days + 1
        if duration_days > max_window_days:
            governance_errors.append(
                f"{window_prefix}: duration {duration_days}d exceeds max_window_days="
                f"{max_window_days}"
            )

        allowances = window.get("allowances", {})
        if not isinstance(allowances, dict):
            governance_errors.append(f"{window_prefix}.allowances: expected mapping")
            continue

        unknown_allowance_keys = sorted(set(allowances) - allowed_allowance_keys)
        if unknown_allowance_keys:
            governance_errors.append(
                f"{window_prefix}.allowances: unknown keys in budget-only mode: "
                f"{unknown_allowance_keys}"
            )

        total_exemptions = allowances.get("total_exemptions", 0)
        registry_budgets = allowances.get("registry_budgets", {})
        group_budgets = allowances.get("group_budgets", {})

        has_positive_total = isinstance(total_exemptions, int) and total_exemptions > 0
        has_positive_registry = isinstance(registry_budgets, dict) and any(
            isinstance(value, int) and value > 0 for value in registry_budgets.values()
        )
        has_positive_group = isinstance(group_budgets, dict) and any(
            isinstance(value, int) and value > 0 for value in group_budgets.values()
        )
        if not (has_positive_total or has_positive_registry or has_positive_group):
            governance_errors.append(
                f"{window_prefix}.allowances: must define at least one positive budget "
                "allowance in budget-only mode"
            )

    return governance_errors


def _print_priority_registry_trend(
    *,
    scorecard_raw: dict[str, object],
    summary_quarter: str,
    summary_by_registry: dict[str, int],
) -> None:
    governance = scorecard_raw.get("governance", {})
    if not isinstance(governance, dict):
        return
    burn_down = governance.get("burn_down_priorities", {})
    if not isinstance(burn_down, dict):
        return
    raw_registries = burn_down.get("registries", [])
    if not isinstance(raw_registries, list):
        return
    priority_registries = [
        item.strip()
        for item in raw_registries
        if isinstance(item, str) and item.strip()
    ]
    if not priority_registries:
        return

    raw_targets = scorecard_raw.get("quarterly_targets", [])
    if not isinstance(raw_targets, list):
        return

    ordered_targets: list[tuple[str, dict[str, int]]] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            continue
        quarter = item.get("quarter")
        registry_budgets = item.get("registry_budgets")
        if not isinstance(quarter, str) or not isinstance(registry_budgets, dict):
            continue
        parsed_quarter = _parse_quarter_label(quarter)
        if parsed_quarter is None:
            continue
        parsed_budgets: dict[str, int] = {}
        for registry_name, value in registry_budgets.items():
            if isinstance(registry_name, str) and isinstance(value, int):
                parsed_budgets[registry_name] = value
        ordered_targets.append((quarter, parsed_budgets))

    if not ordered_targets:
        return
    ordered_targets.sort(key=lambda item: _parse_quarter_label(item[0]) or (0, 0))
    quarter_to_index = {
        quarter: index for index, (quarter, _) in enumerate(ordered_targets)
    }
    current_index = quarter_to_index.get(summary_quarter)
    current_budget_by_registry = (
        ordered_targets[current_index][1] if current_index is not None else {}
    )
    next_budget_by_registry = (
        ordered_targets[current_index + 1][1]
        if current_index is not None and current_index + 1 < len(ordered_targets)
        else {}
    )

    baseline = scorecard_raw.get("baseline", {})
    baseline_by_registry = (
        baseline.get("by_registry", {}) if isinstance(baseline, dict) else {}
    )
    if not isinstance(baseline_by_registry, dict):
        baseline_by_registry = {}

    print("[quality-exemptions] burn-down trend (ratchet-only registries):")
    for registry_name in priority_registries:
        current_count = int(summary_by_registry.get(registry_name, 0))
        baseline_count_raw = baseline_by_registry.get(registry_name, current_count)
        baseline_count = (
            int(baseline_count_raw)
            if isinstance(baseline_count_raw, int)
            else current_count
        )
        current_budget = int(current_budget_by_registry.get(registry_name, 0))
        next_budget = (
            int(next_budget_by_registry[registry_name])
            if registry_name in next_budget_by_registry
            else None
        )
        delta_from_baseline = current_count - baseline_count
        headroom = current_budget - current_count
        if headroom < 0:
            status = "over_budget"
        elif next_budget is not None and current_count > next_budget:
            status = "at_risk_next_quarter"
        else:
            status = "on_track"
        next_budget_label = "-" if next_budget is None else str(next_budget)
        print(
            "  - "
            f"{registry_name}: current={current_count}, "
            f"baseline={baseline_count}, delta_baseline={delta_from_baseline:+d}, "
            f"budget[{summary_quarter}]={current_budget}, headroom={headroom}, "
            f"next_budget={next_budget_label}, status={status}"
        )


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
    temp_window_mode = _resolve_temp_window_mode(
        requested_mode=args.temp_window_mode,
        scorecard_raw=scorecard_raw,
    )
    max_grace_window_days = _resolve_max_grace_window_days(
        scorecard_raw=scorecard_raw,
        fallback_days=args.max_grace_window_days,
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

    if temp_window_mode == "budget-only":
        grace_window_errors = _validate_budget_only_grace_windows(
            scorecard_raw=scorecard_raw,
            today=today,
            max_window_days=max_grace_window_days,
        )
        if grace_window_errors:
            print(
                "[quality-exemptions] budget-only grace-window policy failed "
                f"(max-window-days={max_grace_window_days}):"
            )
            for item in grace_window_errors:
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
    if args.trend_report == "on":
        _print_priority_registry_trend(
            scorecard_raw=scorecard_raw,
            summary_quarter=summary.quarter,
            summary_by_registry=summary.by_registry,
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
        f"violations={len(growth_violations)}, "
        f"temp-window-mode={temp_window_mode}, "
        f"max-window-days={max_grace_window_days})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
