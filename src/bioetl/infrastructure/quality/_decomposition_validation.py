"""Owner/expiry decomposition, priority burndown, and program done criteria validators."""

from __future__ import annotations

from itertools import pairwise

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _validate_non_negative_int,
)


def _collect_quarterly_registry_budgets(
    raw: JsonDict,  # Any: YAML values are heterogeneous
) -> dict[str, dict[str, int]]:
    """Collect validated-looking quarterly registry budgets for monotonic checks."""
    quarterly_targets = raw.get("quarterly_targets", [])
    if not isinstance(quarterly_targets, list):
        return {}

    collected: dict[str, dict[str, int]] = {}
    for item in quarterly_targets:
        if not isinstance(item, dict):
            continue
        quarter = item.get("quarter")
        budgets = item.get("registry_budgets")
        if not isinstance(quarter, str) or not isinstance(budgets, dict):
            continue
        parsed_budgets: dict[str, int] = {}
        for registry_name, value in budgets.items():
            if isinstance(registry_name, str) and isinstance(value, int):
                parsed_budgets[registry_name] = value
        collected[quarter] = parsed_budgets
    return collected


def _validate_owner_diversification_policy(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> tuple[tuple[int, int] | None, int]:
    """Validate governance.owner_diversification and return normalized settings."""
    governance = raw.get("governance", {})
    if not isinstance(governance, dict):
        return None, 1

    policy = governance.get("owner_diversification", {})
    if not isinstance(policy, dict):
        errors.append("governance.owner_diversification: expected mapping")
        return None, 1

    starts_quarter = policy.get("starts_quarter")
    parsed_starts = None
    if not isinstance(starts_quarter, str):
        errors.append(
            "governance.owner_diversification.starts_quarter: expected quarter label"
        )
    else:
        parsed_starts = _parse_quarter_label(starts_quarter)
        if parsed_starts is None:
            errors.append(
                "governance.owner_diversification.starts_quarter: expected 'YYYY-QN' format"
            )

    min_distinct = _validate_non_negative_int(
        policy.get("min_distinct_owners"),
        field_name="governance.owner_diversification.min_distinct_owners",
        errors=errors,
    )
    if min_distinct is None:
        min_distinct = 1
    if min_distinct < 1:
        errors.append(
            "governance.owner_diversification.min_distinct_owners: must be >= 1"
        )
        min_distinct = 1

    return parsed_starts, min_distinct


def _validate_owner_decomposition_targets_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    quarter_budget_map: dict[str, int],
    owner_diversification_start: tuple[int, int] | None,
    min_distinct_owners: int,
    errors: list[str],
) -> None:
    """Validate owner decomposition targets against quarterly max budgets."""
    targets = raw.get("owner_decomposition_targets")
    if not isinstance(targets, list) or not targets:
        errors.append("owner_decomposition_targets: required non-empty list")
        return

    seen_quarters: set[str] = set()
    for index, item in enumerate(targets):
        prefix = f"owner_decomposition_targets[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        quarter = item.get("quarter")
        if not isinstance(quarter, str):
            errors.append(f"{prefix}.quarter: expected string")
            continue
        parsed_quarter = _parse_quarter_label(quarter)
        if parsed_quarter is None:
            errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
            continue
        if quarter in seen_quarters:
            errors.append(f"{prefix}.quarter: duplicate quarter '{quarter}'")
            continue
        seen_quarters.add(quarter)

        if quarter not in quarter_budget_map:
            errors.append(
                f"{prefix}.quarter: unknown quarter '{quarter}' (not in quarterly_targets)"
            )
            continue

        allocations = item.get("allocations")
        if not isinstance(allocations, dict) or not allocations:
            errors.append(f"{prefix}.allocations: expected non-empty mapping")
            continue

        parsed_allocations: dict[str, int] = {}
        for owner, value in allocations.items():
            if not isinstance(owner, str) or not owner.strip():
                errors.append(f"{prefix}.allocations: owner must be non-empty string")
                continue
            parsed_value = _validate_non_negative_int(
                value,
                field_name=f"{prefix}.allocations.{owner}",
                errors=errors,
            )
            if parsed_value is not None:
                parsed_allocations[owner] = parsed_value

        if sum(parsed_allocations.values()) != quarter_budget_map[quarter]:
            errors.append(
                f"{prefix}.allocations: sum {sum(parsed_allocations.values())} "
                f"must equal quarterly_targets[{quarter}].max_total_exemptions "
                f"{quarter_budget_map[quarter]}"
            )

        if (
            owner_diversification_start is not None
            and parsed_quarter >= owner_diversification_start
            and len(parsed_allocations) < min_distinct_owners
        ):
            errors.append(
                f"{prefix}.allocations: expected at least {min_distinct_owners} owners "
                f"starting from quarter "
                f"{owner_diversification_start[0]}-Q{owner_diversification_start[1]}"
            )


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
        quarter = item.get("quarter")
        if not isinstance(quarter, str):
            errors.append(f"{prefix}.quarter: expected string")
            continue
        parsed_quarter = _parse_quarter_label(quarter)
        if parsed_quarter is None:
            errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
            continue
        if quarter in seen_quarters:
            errors.append(f"{prefix}.quarter: duplicate quarter '{quarter}'")
            continue
        seen_quarters.add(quarter)

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

    registries = burn_down.get("registries")
    if not isinstance(registries, list) or not registries:
        errors.append(
            "governance.burn_down_priorities.registries: expected non-empty list"
        )
        return

    priority_registries: list[str] = []
    for item in registries:
        if not isinstance(item, str) or not item.strip():
            errors.append(
                "governance.burn_down_priorities.registries: registry names must be non-empty strings"
            )
            continue
        registry_name = item.strip()
        if registry_name not in baseline_registry_names:
            errors.append(
                "governance.burn_down_priorities.registries: "
                f"unknown registry '{registry_name}'"
            )
            continue
        priority_registries.append(registry_name)

    by_quarter_registry_budgets = _collect_quarterly_registry_budgets(raw)
    ordered_quarters = sorted(
        (
            quarter,
            _parse_quarter_label(quarter),
        )
        for quarter in by_quarter_registry_budgets
        if _parse_quarter_label(quarter) is not None
    )
    ordered_quarter_names = [quarter for quarter, _ in ordered_quarters]

    for registry_name in priority_registries:
        previous: int | None = None
        for quarter in ordered_quarter_names:
            current = by_quarter_registry_budgets[quarter].get(registry_name)
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


def _validate_program_done_criteria_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> None:
    """Validate long-horizon program done criteria section."""
    section = raw.get("program_done_criteria")
    if not isinstance(section, dict):
        errors.append("program_done_criteria: required mapping")
        return

    _validate_non_negative_int(
        section.get("max_total_exemptions"),
        field_name="program_done_criteria.max_total_exemptions",
        errors=errors,
    )

    min_score = section.get("min_integral_score")
    if not isinstance(min_score, (int, float)):
        errors.append("program_done_criteria.min_integral_score: expected number")
    elif not (0 <= float(min_score) <= 100):
        errors.append(
            "program_done_criteria.min_integral_score: must be between 0 and 100"
        )

    _validate_non_negative_int(
        section.get("max_expired_entries"),
        field_name="program_done_criteria.max_expired_entries",
        errors=errors,
    )

    deadline_quarter = section.get("deadline_quarter")
    if (
        not isinstance(deadline_quarter, str)
        or _parse_quarter_label(deadline_quarter) is None
    ):
        errors.append(
            "program_done_criteria.deadline_quarter: expected 'YYYY-QN' format"
        )
