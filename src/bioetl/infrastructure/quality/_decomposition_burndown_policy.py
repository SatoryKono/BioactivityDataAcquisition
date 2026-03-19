"""Burndown and expiry policy helpers for debt scorecard decomposition checks."""

from __future__ import annotations

from itertools import pairwise

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._decomposition_owner_policy import (
    _collect_quarterly_registry_budgets,
)
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _validate_non_negative_int,
)


def _validate_expiry_target_quarter(
    item: JsonDict,  # Any: YAML values are heterogeneous
    prefix: str,
    seen_quarters: set[str],
    errors: list[str],
) -> tuple[int, int] | None:
    """Validate quarter field of a single expiry target entry."""
    quarter = item.get("quarter")
    if not isinstance(quarter, str):
        errors.append(f"{prefix}.quarter: expected string")
        return None
    parsed_quarter = _parse_quarter_label(quarter)
    if parsed_quarter is None:
        errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
        return None
    if quarter in seen_quarters:
        errors.append(f"{prefix}.quarter: duplicate quarter '{quarter}'")
        return None
    seen_quarters.add(quarter)
    return parsed_quarter


def _validate_expiry_decomposition_targets_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> None:
    """Validate expiry decomposition targets as monotonically decreasing caps."""
    targets = raw.get("expiry_decomposition_targets")
    if not isinstance(targets, list) or not targets:
        errors.append("expiry_decomposition_targets: required non-empty list")
        return

    parsed: list[tuple[tuple[int, int], int]] = []
    seen_quarters: set[str] = set()
    for index, item in enumerate(targets):
        prefix = f"expiry_decomposition_targets[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        parsed_quarter = _validate_expiry_target_quarter(
            item, prefix, seen_quarters, errors
        )
        if parsed_quarter is None:
            continue

        max_entries = _validate_non_negative_int(
            item.get("max_entries_expiring_in_quarter"),
            field_name=f"{prefix}.max_entries_expiring_in_quarter",
            errors=errors,
        )
        if max_entries is not None:
            parsed.append((parsed_quarter, max_entries))

    ordered = [value for _, value in sorted(parsed, key=lambda x: x[0])]
    for previous, current in pairwise(ordered):
        if current > previous:
            errors.append(
                "expiry_decomposition_targets: "
                "max_entries_expiring_in_quarter must be non-increasing"
            )


def _validate_burndown_registries(
    registries_raw: object,
    baseline_registry_names: set[str],
    errors: list[str],
) -> list[str]:
    """Parse and validate the burn-down registries list."""
    if not isinstance(registries_raw, list) or not registries_raw:
        errors.append(
            "governance.burn_down_priorities.registries: expected non-empty list"
        )
        return []

    result: list[str] = []
    for item in registries_raw:
        if not isinstance(item, str) or not item.strip():
            errors.append(
                "governance.burn_down_priorities.registries: "
                "registry names must be non-empty strings"
            )
            continue
        registry_name = item.strip()
        if registry_name not in baseline_registry_names:
            errors.append(
                "governance.burn_down_priorities.registries: "
                f"unknown registry '{registry_name}'"
            )
            continue
        result.append(registry_name)
    return result


def _validate_single_registry_burndown(
    registry_name: str,
    ordered_quarters: list[str],
    by_quarter_budgets: dict[str, dict[str, int]],
    errors: list[str],
) -> None:
    """Validate strict quarter-over-quarter decrease for one registry."""
    previous: int | None = None
    for quarter in ordered_quarters:
        current = by_quarter_budgets[quarter].get(registry_name)
        if current is None:
            errors.append(
                f"quarterly_targets[{quarter}].registry_budgets missing '{registry_name}'"
            )
            continue
        if previous is not None and current >= previous:
            errors.append(
                "quarterly_targets registry burn-down violation: "
                f"'{registry_name}' budget must strictly decrease ({current} >= {previous})"
            )
        previous = current


def _validate_priority_registry_burndown(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    errors: list[str],
) -> None:
    """Validate strict quarter-over-quarter burn-down for priority registries."""
    governance = raw.get("governance", {})
    if not isinstance(governance, dict):
        return

    burn_down = governance.get("burn_down_priorities", {})
    if not isinstance(burn_down, dict):
        errors.append("governance.burn_down_priorities: expected mapping")
        return

    priority_registries = _validate_burndown_registries(
        burn_down.get("registries"), baseline_registry_names, errors
    )

    by_quarter_registry_budgets = _collect_quarterly_registry_budgets(raw)
    ordered_quarters = sorted(
        (quarter, _parse_quarter_label(quarter))
        for quarter in by_quarter_registry_budgets
        if _parse_quarter_label(quarter) is not None
    )
    ordered_quarter_names = [quarter for quarter, _ in ordered_quarters]

    for registry_name in priority_registries:
        _validate_single_registry_burndown(
            registry_name,
            ordered_quarter_names,
            by_quarter_registry_budgets,
            errors,
        )


__all__ = [
    "_validate_burndown_registries",
    "_validate_expiry_decomposition_targets_section",
    "_validate_expiry_target_quarter",
    "_validate_priority_registry_burndown",
]
