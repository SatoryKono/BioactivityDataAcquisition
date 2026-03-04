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
    rf_id_str = rf_id if isinstance(rf_id, str) else None
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
