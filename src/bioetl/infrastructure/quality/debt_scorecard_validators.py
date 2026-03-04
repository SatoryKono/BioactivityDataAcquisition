"""Validation helpers for debt scorecard schema."""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import Any

from bioetl.infrastructure.quality.debt_scorecard import (
    _parse_iso_date,
    _parse_quarter_label,
)


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
) -> tuple[tuple[int, int], dict[str, Any]] | None:
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
    return quarter_tuple, target


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

    parsed_targets: list[tuple[tuple[int, int], dict[str, Any]]] = []
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
    errors: list[str],
) -> None:
    rf_id = window.get("rf_id")
    approved = window.get("approved")
    starts_on = _parse_iso_date(window.get("starts_on"))
    ends_on = _parse_iso_date(window.get("ends_on"))

    if not isinstance(rf_id, str) or not rf_id.strip():
        errors.append(f"{prefix}.rf_id: required non-empty string")
    if not isinstance(approved, bool):
        errors.append(f"{prefix}.approved: expected bool")
    if approved and isinstance(rf_id, str) and not rf_id.startswith("RF-"):
        errors.append(f"{prefix}.rf_id: approved grace window must reference RF-*")
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

        _validate_grace_window_metadata(prefix=prefix, window=window, errors=errors)
        _validate_allowances(
            allowances=window.get("allowances", {}),
            prefix=prefix,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
            errors=errors,
        )
