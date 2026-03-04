"""Validation helpers for debt scorecard schema/governance checks."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from itertools import pairwise
from typing import Any, TypedDict, cast

_QUARTER_RE = re.compile(r"^(20\d{2})-Q([1-4])$")


class QuarterTarget(TypedDict):
    """Normalized quarterly target entry."""

    quarter: str
    max_total_exemptions: int
    min_integral_score: int | float
    group_budgets: dict[str, int]
    registry_budgets: dict[str, int]


def _parse_iso_date(raw_value: object) -> date | None:
    if not isinstance(raw_value, str):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _parse_quarter_label(value: str) -> tuple[int, int] | None:
    match = _QUARTER_RE.fullmatch(value.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _validate_non_negative_int(
    value: object,
    *,
    field_name: str,
    errors: list[str],
) -> int | None:
    if not isinstance(value, int):
        errors.append(f"{field_name}: expected int, got {type(value).__name__}")
        return None
    if value < 0:
        errors.append(f"{field_name}: expected non-negative int, got {value}")
        return None
    return value


def _validate_gate_mode(
    *,
    value: object,
    field_name: str,
    errors: list[str],
) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{field_name}: expected string ('warn' or 'block')")
        return None
    mode = value.strip().lower()
    if mode not in {"warn", "block"}:
        errors.append(f"{field_name}: expected 'warn' or 'block', got {value!r}")
        return None
    return mode


def _validate_baseline_section(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
    errors: list[str],
) -> tuple[int | None, dict[str, int]] | None:
    baseline = raw.get("baseline")
    if not isinstance(baseline, dict):
        errors.append("baseline: required mapping")
        return None

    baseline_total = _validate_non_negative_int(
        baseline.get("total_exemptions"),
        field_name="baseline.total_exemptions",
        errors=errors,
    )

    baseline_by_registry = baseline.get("by_registry")
    if not isinstance(baseline_by_registry, dict) or not baseline_by_registry:
        errors.append("baseline.by_registry: required non-empty mapping")
        return None

    normalized_registry_counts: dict[str, int] = {}
    for registry_name, count in sorted(baseline_by_registry.items()):
        if not isinstance(registry_name, str) or not registry_name.strip():
            errors.append(
                "baseline.by_registry: registry name must be non-empty string"
            )
            continue
        parsed = _validate_non_negative_int(
            count,
            field_name=f"baseline.by_registry.{registry_name}",
            errors=errors,
        )
        if parsed is not None:
            normalized_registry_counts[registry_name] = parsed

    if baseline_total is not None and baseline_total != sum(
        normalized_registry_counts.values()
    ):
        errors.append(
            "baseline.total_exemptions must equal sum(baseline.by_registry.*)"
        )

    return baseline_total, normalized_registry_counts


def _validate_registry_group_entry(
    *,
    group_name: str,
    group_data: object,
    errors: list[str],
) -> tuple[str, ...] | None:
    if not isinstance(group_data, dict):
        errors.append(f"registry_groups.{group_name}: expected mapping")
        return None
    registries = group_data.get("registries")
    if not isinstance(registries, list) or not registries:
        errors.append(
            f"registry_groups.{group_name}.registries: expected non-empty list"
        )
        return None

    clean: list[str] = []
    for item in registries:
        if not isinstance(item, str) or not item.strip():
            errors.append(
                f"registry_groups.{group_name}.registries: invalid registry name"
            )
            continue
        clean.append(item)
    return tuple(clean)


def _validate_registry_groups_section(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    errors: list[str],
) -> dict[str, tuple[str, ...]]:
    registry_groups = raw.get("registry_groups")
    if not isinstance(registry_groups, dict) or not registry_groups:
        errors.append("registry_groups: required non-empty mapping")
        return {}

    grouped_registries: list[str] = []
    normalized_groups: dict[str, tuple[str, ...]] = {}
    for group_name, group_data in sorted(registry_groups.items()):
        if not isinstance(group_name, str) or not group_name.strip():
            errors.append("registry_groups: group name must be non-empty string")
            continue
        parsed = _validate_registry_group_entry(
            group_name=group_name,
            group_data=group_data,
            errors=errors,
        )
        if parsed is None:
            continue
        normalized_groups[group_name] = parsed
        grouped_registries.extend(parsed)

    grouped_counter = Counter(grouped_registries)
    duplicates = sorted(name for name, count in grouped_counter.items() if count > 1)
    if duplicates:
        errors.append(
            f"registry_groups: registries listed in multiple groups: {duplicates}"
        )

    grouped_registry_names = set(grouped_counter)
    missing_groups = sorted(baseline_registry_names - grouped_registry_names)
    extra_groups = sorted(grouped_registry_names - baseline_registry_names)
    if missing_groups:
        errors.append(f"registry_groups: missing baseline registries {missing_groups}")
    if extra_groups:
        errors.append(f"registry_groups: unknown registries {extra_groups}")
    return normalized_groups


def _is_valid_rollout_section_key(
    *,
    key: str,
    baseline_registry_names: set[str],
    group_names: set[str],
) -> bool:
    if key in {"*", "total_exemptions", "integral_score"}:
        return True

    if key == "registry:*":
        return True
    if key.startswith("registry:"):
        registry_name = key.split(":", 1)[1]
        return registry_name in baseline_registry_names

    if key == "group:*":
        return True
    if key.startswith("group:"):
        group_name = key.split(":", 1)[1]
        return group_name in group_names

    return False


def _validate_governance_section(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> bool:
    governance = raw.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance: required mapping")
        return False

    _validate_gate_mode(
        value=governance.get("growth_gate_default_mode", "block"),
        field_name="governance.growth_gate_default_mode",
        errors=errors,
    )

    allow_rf_only = governance.get("allow_grace_windows_only_for_rf")
    allow_rf_only_flag = False
    if not isinstance(allow_rf_only, bool):
        errors.append("governance.allow_grace_windows_only_for_rf: expected bool")
    else:
        allow_rf_only_flag = allow_rf_only

    rollout = governance.get("growth_section_gate_rollout", {})
    if not isinstance(rollout, dict):
        errors.append("governance.growth_section_gate_rollout: expected mapping")
        return allow_rf_only_flag

    _validate_gate_mode(
        value=rollout.get(
            "default_mode", governance.get("growth_gate_default_mode", "block")
        ),
        field_name="governance.growth_section_gate_rollout.default_mode",
        errors=errors,
    )

    warn_until = rollout.get("warn_until_by_section", {})
    if not isinstance(warn_until, dict):
        errors.append(
            "governance.growth_section_gate_rollout.warn_until_by_section: expected mapping"
        )
        return allow_rf_only_flag

    for section_key, cutoff in sorted(warn_until.items()):
        if not isinstance(section_key, str) or not section_key.strip():
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section: "
                "section key must be non-empty string"
            )
            continue
        if not _is_valid_rollout_section_key(
            key=section_key,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
        ):
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section: "
                f"unknown section key '{section_key}'"
            )
            continue
        if _parse_iso_date(cutoff) is None:
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section."
                f"{section_key}: expected ISO date (YYYY-MM-DD)"
            )

    return allow_rf_only_flag


def _validate_budget_mapping(
    mapping: object,
    *,
    expected_keys: set[str],
    field_name: str,
    errors: list[str],
) -> None:
    if not isinstance(mapping, dict):
        errors.append(f"{field_name}: expected mapping")
        return

    missing_keys = sorted(expected_keys - set(mapping))
    extra_keys = sorted(set(mapping) - expected_keys)
    if missing_keys:
        errors.append(f"{field_name}: missing entries {missing_keys}")
    if extra_keys:
        errors.append(f"{field_name}: unknown entries {extra_keys}")

    for key, value in mapping.items():
        _validate_non_negative_int(
            value,
            field_name=f"{field_name}.{key}",
            errors=errors,
        )


def _validate_quarter_target(
    *,
    index: int,
    target: object,
    group_names: set[str],
    baseline_registry_names: set[str],
    errors: list[str],
) -> (
    tuple[
        tuple[int, int],
        QuarterTarget,
    ]
    | None
):
    prefix = f"quarterly_targets[{index}]"
    if not isinstance(target, dict):
        errors.append(f"{prefix}: expected mapping")
        return None

    quarter = target.get("quarter")
    parsed_quarter = quarter if isinstance(quarter, str) else ""
    quarter_tuple = _parse_quarter_label(parsed_quarter)
    if quarter_tuple is None:
        errors.append(f"{prefix}.quarter: expected 'YYYY-QN' format")
        return None

    max_total = _validate_non_negative_int(
        target.get("max_total_exemptions"),
        field_name=f"{prefix}.max_total_exemptions",
        errors=errors,
    )
    min_score = target.get("min_integral_score")
    if not isinstance(min_score, (int, float)):
        errors.append(f"{prefix}.min_integral_score: expected number")
    elif not (0 <= float(min_score) <= 100):
        errors.append(f"{prefix}.min_integral_score: must be between 0 and 100")

    _validate_budget_mapping(
        target.get("group_budgets"),
        expected_keys=group_names,
        field_name=f"{prefix}.group_budgets",
        errors=errors,
    )
    _validate_budget_mapping(
        target.get("registry_budgets"),
        expected_keys=baseline_registry_names,
        field_name=f"{prefix}.registry_budgets",
        errors=errors,
    )

    if max_total is None or not isinstance(min_score, (int, float)):
        return None
    return quarter_tuple, cast(QuarterTarget, target)


def _validate_quarterly_targets_section(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
    *,
    group_names: set[str],
    baseline_registry_names: set[str],
    errors: list[str],
) -> None:
    quarterly_targets = raw.get("quarterly_targets")
    if not isinstance(quarterly_targets, list) or not quarterly_targets:
        errors.append("quarterly_targets: required non-empty list")
        return

    parsed_targets: list[tuple[tuple[int, int], QuarterTarget]] = []
    seen_quarters: set[str] = set()
    for index, target in enumerate(quarterly_targets):
        parsed = _validate_quarter_target(
            index=index,
            target=target,
            group_names=group_names,
            baseline_registry_names=baseline_registry_names,
            errors=errors,
        )
        if parsed is None:
            continue
        quarter = str(parsed[1]["quarter"])
        if quarter in seen_quarters:
            errors.append(
                f"quarterly_targets[{index}].quarter: duplicate quarter '{quarter}'"
            )
            continue
        seen_quarters.add(quarter)
        parsed_targets.append(parsed)

    ordered_targets = [
        item[1] for item in sorted(parsed_targets, key=lambda item: item[0])
    ]
    for previous, current in pairwise(ordered_targets):
        prev_total = int(previous["max_total_exemptions"])
        curr_total = int(current["max_total_exemptions"])
        if curr_total >= prev_total:
            errors.append(
                "quarterly_targets: max_total_exemptions must strictly decrease each quarter"
            )

        prev_score = float(previous["min_integral_score"])
        curr_score = float(current["min_integral_score"])
        if curr_score <= prev_score:
            errors.append(
                "quarterly_targets: min_integral_score must strictly increase each quarter"
            )


def _validate_allowances(
    *,
    allowances: object,
    prefix: str,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> None:
    if not isinstance(allowances, dict):
        errors.append(f"{prefix}.allowances: expected mapping")
        return

    _validate_non_negative_int(
        allowances.get("total_exemptions", 0),
        field_name=f"{prefix}.allowances.total_exemptions",
        errors=errors,
    )

    registry_allowances = allowances.get("registry_budgets", {})
    if not isinstance(registry_allowances, dict):
        errors.append(f"{prefix}.allowances.registry_budgets: expected mapping")
    else:
        for registry_name, value in registry_allowances.items():
            if registry_name not in baseline_registry_names:
                errors.append(
                    f"{prefix}.allowances.registry_budgets: unknown registry '{registry_name}'"
                )
                continue
            _validate_non_negative_int(
                value,
                field_name=f"{prefix}.allowances.registry_budgets.{registry_name}",
                errors=errors,
            )

    group_allowances = allowances.get("group_budgets", {})
    if not isinstance(group_allowances, dict):
        errors.append(f"{prefix}.allowances.group_budgets: expected mapping")
        return
    for group_name, value in group_allowances.items():
        if group_name not in group_names:
            errors.append(
                f"{prefix}.allowances.group_budgets: unknown group '{group_name}'"
            )
            continue
        _validate_non_negative_int(
            value,
            field_name=f"{prefix}.allowances.group_budgets.{group_name}",
            errors=errors,
        )


def _validate_grace_window_metadata(
    *,
    prefix: str,
    window: dict[str, Any],  # Any: YAML values are heterogeneous
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    rf_id = window.get("rf_id")
    approved = window.get("approved")
    starts_on = _parse_iso_date(window.get("starts_on"))
    ends_on = _parse_iso_date(window.get("ends_on"))

    _validate_grace_window_identity_fields(
        prefix=prefix,
        rf_id=rf_id,
        approved=approved,
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )
    _validate_grace_window_dates(
        prefix=prefix,
        starts_on=starts_on,
        ends_on=ends_on,
        errors=errors,
    )


def _validate_grace_window_identity_fields(
    *,
    prefix: str,
    rf_id: object,
    approved: object,
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    rf_id_str: str | None = rf_id if isinstance(rf_id, str) else None
    rf_id_is_valid = rf_id_str is not None and bool(rf_id_str.strip())
    rf_id_is_rf_ref = rf_id_str is not None and rf_id_str.startswith("RF-")
    approved_is_bool = isinstance(approved, bool)

    if not rf_id_is_valid:
        errors.append(f"{prefix}.rf_id: required non-empty string")

    if not approved_is_bool:
        errors.append(f"{prefix}.approved: expected bool")
        return

    if allow_rf_only_for_rf and approved is False:
        errors.append(
            f"{prefix}.approved: must be true when "
            "governance.allow_grace_windows_only_for_rf=true"
        )
    if approved and rf_id_is_valid and not rf_id_is_rf_ref:
        errors.append(f"{prefix}.rf_id: approved grace window must reference RF-*")
    if allow_rf_only_for_rf and rf_id_is_valid and not rf_id_is_rf_ref:
        errors.append(
            f"{prefix}.rf_id: must reference RF-* when "
            "governance.allow_grace_windows_only_for_rf=true"
        )


def _validate_grace_window_dates(
    *,
    prefix: str,
    starts_on: date | None,
    ends_on: date | None,
    errors: list[str],
) -> None:
    if starts_on is None:
        errors.append(f"{prefix}.starts_on: expected ISO date")
    if ends_on is None:
        errors.append(f"{prefix}.ends_on: expected ISO date")
    if starts_on is not None and ends_on is not None and ends_on < starts_on:
        errors.append(f"{prefix}: ends_on must be >= starts_on")


def _validate_grace_windows_section(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    grace_windows = raw.get("grace_windows", [])
    if grace_windows is None:
        grace_windows = []
    if not isinstance(grace_windows, list):
        errors.append("grace_windows: expected list")
        return

    for index, window in enumerate(grace_windows):
        prefix = f"grace_windows[{index}]"
        if not isinstance(window, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        _validate_grace_window_metadata(
            prefix=prefix,
            window=window,
            allow_rf_only_for_rf=allow_rf_only_for_rf,
            errors=errors,
        )
        _validate_allowances(
            allowances=window.get("allowances", {}),
            prefix=prefix,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
            errors=errors,
        )


def _collect_quarterly_registry_budgets(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
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


def validate_debt_scorecard_structure(
    raw: dict[str, Any],  # Any: YAML values are heterogeneous
) -> list[str]:
    """Validate debt scorecard schema and monotonic governance targets."""
    errors: list[str] = []

    schema_version = raw.get("schema_version")
    if schema_version != 1:
        errors.append(f"schema_version must be 1, got {schema_version!r}")

    baseline_result = _validate_baseline_section(raw, errors)
    if baseline_result is None:
        return errors
    _, normalized_registry_counts = baseline_result

    baseline_registry_names = set(normalized_registry_counts)
    normalized_groups = _validate_registry_groups_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    if not normalized_groups:
        return errors

    allow_rf_only_for_rf = _validate_governance_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        group_names=set(normalized_groups),
        errors=errors,
    )

    _validate_quarterly_targets_section(
        raw,
        group_names=set(normalized_groups),
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    quarter_budget_map = {
        str(item["quarter"]): int(item["max_total_exemptions"])
        for item in raw.get("quarterly_targets", [])
        if isinstance(item, dict)
        and isinstance(item.get("quarter"), str)
        and isinstance(item.get("max_total_exemptions"), int)
    }
    owner_div_start, min_distinct_owners = _validate_owner_diversification_policy(
        raw,
        errors,
    )
    _validate_owner_decomposition_targets_section(
        raw,
        quarter_budget_map=quarter_budget_map,
        owner_diversification_start=owner_div_start,
        min_distinct_owners=min_distinct_owners,
        errors=errors,
    )
    _validate_expiry_decomposition_targets_section(raw, errors)
    _validate_priority_registry_burndown(
        raw,
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )
    _validate_program_done_criteria_section(raw, errors)
    _validate_grace_windows_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        group_names=set(normalized_groups),
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )

    return errors


validate_debt_scorecard_raw = validate_debt_scorecard_structure


__all__ = ["validate_debt_scorecard_raw", "validate_debt_scorecard_structure"]
