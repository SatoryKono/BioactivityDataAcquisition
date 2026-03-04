"""Scorecard governance for architecture metric exemptions."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry

_DEFAULT_SCORECARD_PATH = Path("configs/quality/debt_scorecard.yaml")
_QUARTER_RE = re.compile(r"^(20\d{2})-Q([1-4])$")


@dataclass(frozen=True)
class ExemptionInventory:
    """Aggregated exemption inventory for governance calculations."""

    total_exemptions: int
    by_registry: dict[str, int]
    by_owner: dict[str, int]
    by_expiry_quarter: dict[str, int]
    expired_entries: int


@dataclass(frozen=True)
class DebtScorecardEvaluation:
    """Result of scorecard budget evaluation."""

    quarter: str
    integral_score: float
    total_exemptions: int
    total_budget: int
    active_grace_windows: tuple[str, ...]
    by_registry: dict[str, int]
    by_group: dict[str, int]
    by_owner: dict[str, int]
    by_expiry_quarter: dict[str, int]
    expired_entries: int


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_scorecard_path(path: Path | str | None = None) -> Path:
    candidate = _DEFAULT_SCORECARD_PATH if path is None else Path(path)
    if candidate.is_absolute():
        return candidate
    return _project_root() / candidate


def _parse_iso_date(raw_value: object) -> date | None:
    if not isinstance(raw_value, str):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _quarter_label(target_date: date) -> str:
    quarter = ((target_date.month - 1) // 3) + 1
    return f"{target_date.year}-Q{quarter}"


def _parse_quarter_label(value: str) -> tuple[int, int] | None:
    match = _QUARTER_RE.fullmatch(value.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def load_debt_scorecard(
    path: Path | str | None = None,
) -> dict[str, Any]:  # Any: scorecard sections are heterogeneous
    """Load debt scorecard YAML as dictionary."""
    scorecard_path = _resolve_scorecard_path(path)
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Debt scorecard not found: {scorecard_path}")

    raw = yaml.safe_load(scorecard_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Debt scorecard must be a mapping: {scorecard_path}")
    return raw


def build_exemption_inventory(
    registry_path: Path | str | None = None,
    *,
    today: date | None = None,
) -> ExemptionInventory:
    """Build aggregated inventory from the exemptions registry."""
    now = today or date.today()
    raw = load_exemptions_registry(registry_path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    by_registry: Counter[str] = Counter()
    by_owner: Counter[str] = Counter()
    by_expiry_quarter: Counter[str] = Counter()
    expired_entries = 0

    for registry_name, entries in registries.items():
        if not isinstance(entries, dict):
            continue

        for entry in entries.values():
            if not isinstance(entry, dict):
                continue

            by_registry[registry_name] += 1

            owner = entry.get("owner")
            owner_name = owner.strip() if isinstance(owner, str) and owner.strip() else "<missing>"
            by_owner[owner_name] += 1

            expiry_date = _parse_iso_date(entry.get("expires_on"))
            if expiry_date is None:
                by_expiry_quarter["unknown"] += 1
            else:
                by_expiry_quarter[_quarter_label(expiry_date)] += 1
                if expiry_date < now:
                    expired_entries += 1

    return ExemptionInventory(
        total_exemptions=sum(by_registry.values()),
        by_registry=dict(sorted(by_registry.items())),
        by_owner=dict(sorted(by_owner.items())),
        by_expiry_quarter=dict(sorted(by_expiry_quarter.items())),
        expired_entries=expired_entries,
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
            errors.append("baseline.by_registry: registry name must be non-empty string")
            continue
        parsed = _validate_non_negative_int(
            count,
            field_name=f"baseline.by_registry.{registry_name}",
            errors=errors,
        )
        if parsed is not None:
            normalized_registry_counts[registry_name] = parsed

    if baseline_total is not None and baseline_total != sum(normalized_registry_counts.values()):
        errors.append("baseline.total_exemptions must equal sum(baseline.by_registry.*)")

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
        errors.append(f"registry_groups.{group_name}.registries: expected non-empty list")
        return None

    clean: list[str] = []
    for item in registries:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"registry_groups.{group_name}.registries: invalid registry name")
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
        errors.append(f"registry_groups: registries listed in multiple groups: {duplicates}")

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
            errors.append(f"quarterly_targets[{index}].quarter: duplicate quarter '{quarter}'")
            continue
        seen_quarters.add(quarter)
        parsed_targets.append(parsed)

    ordered_targets = [item[1] for item in sorted(parsed_targets, key=lambda item: item[0])]
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
            errors.append(f"{prefix}.allowances.group_budgets: unknown group '{group_name}'")
            continue
        _validate_non_negative_int(
            value,
            field_name=f"{prefix}.allowances.group_budgets.{group_name}",
            errors=errors,
        )


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

        _validate_allowances(
            allowances=window.get("allowances", {}),
            prefix=prefix,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
            errors=errors,
        )


def validate_debt_scorecard(
    path: Path | str | None = None,
) -> list[str]:
    """Validate debt scorecard schema and monotonic governance targets."""
    errors: list[str] = []
    raw = load_debt_scorecard(path)

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
        errors=errors,
    )

    return errors


def compute_integral_debt_score(
    *,
    total_exemptions: int,
    expired_entries: int,
    baseline_total: int,
) -> float:
    """Compute integral debt score (0..100), higher is better."""
    if baseline_total <= 0:
        return 0.0

    debt_reduction_component = max(
        0.0,
        min(100.0, 100.0 - (total_exemptions / baseline_total) * 100.0),
    )
    if total_exemptions <= 0:
        expiry_health_component = 100.0
    else:
        expiry_health_component = max(
            0.0,
            100.0 - (expired_entries / total_exemptions) * 100.0,
        )
    return round((0.7 * expiry_health_component) + (0.3 * debt_reduction_component), 2)


def _current_quarter_target(
    scorecard: dict[str, Any],  # Any: YAML scorecard sections are heterogeneous
    *,
    today: date,
) -> dict[str, Any] | None:
    quarter = _quarter_label(today)
    for item in scorecard.get("quarterly_targets", []):
        if isinstance(item, dict) and item.get("quarter") == quarter:
            return item
    return None


def _is_active_grace_window(
    window: object,
    *,
    today: date,
) -> bool:
    if not isinstance(window, dict) or not window.get("approved"):
        return False
    starts_on = _parse_iso_date(window.get("starts_on"))
    ends_on = _parse_iso_date(window.get("ends_on"))
    if starts_on is None or ends_on is None:
        return False
    return starts_on <= today <= ends_on


def _collect_allowances(
    active_windows: list[dict[str, Any]],  # Any: YAML values are heterogeneous
) -> tuple[int, Counter[str], Counter[str]]:
    allowance_total = 0
    allowance_by_registry: Counter[str] = Counter()
    allowance_by_group: Counter[str] = Counter()

    for window in active_windows:
        allowances = window.get("allowances", {})
        if not isinstance(allowances, dict):
            continue

        allowance_total += int(allowances.get("total_exemptions", 0))

        reg_allowances = allowances.get("registry_budgets", {})
        if isinstance(reg_allowances, dict):
            for registry_name, value in reg_allowances.items():
                if isinstance(value, int):
                    allowance_by_registry[registry_name] += value

        group_allowances = allowances.get("group_budgets", {})
        if isinstance(group_allowances, dict):
            for group_name, value in group_allowances.items():
                if isinstance(value, int):
                    allowance_by_group[group_name] += value

    return allowance_total, allowance_by_registry, allowance_by_group


def _evaluate_registry_budgets(
    *,
    by_registry: dict[str, int],
    target_registry_budgets: dict[str, int],
    allowance_by_registry: Counter[str],
) -> list[str]:
    violations: list[str] = []
    for registry_name, current_count in sorted(by_registry.items()):
        budget = int(target_registry_budgets[registry_name]) + allowance_by_registry.get(
            registry_name, 0
        )
        if current_count > budget:
            violations.append(
                f"registry '{registry_name}' count {current_count} exceeds budget {budget}"
            )
    return violations


def _compute_group_counts(
    *,
    by_registry: dict[str, int],
    registry_groups: dict[str, Any],  # Any: YAML values are heterogeneous
) -> dict[str, int]:
    by_group: dict[str, int] = {}
    for group_name, group_cfg in sorted(registry_groups.items()):
        registries = group_cfg["registries"]
        by_group[group_name] = sum(by_registry.get(name, 0) for name in registries)
    return by_group


def _evaluate_group_budgets(
    *,
    by_group: dict[str, int],
    target_group_budgets: dict[str, int],
    allowance_by_group: Counter[str],
) -> list[str]:
    violations: list[str] = []
    for group_name, group_count in sorted(by_group.items()):
        group_budget = int(target_group_budgets[group_name]) + allowance_by_group.get(
            group_name, 0
        )
        if group_count > group_budget:
            violations.append(
                f"group '{group_name}' count {group_count} exceeds budget {group_budget}"
            )
    return violations


def evaluate_debt_scorecard(
    *,
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    today: date | None = None,
) -> tuple[list[str], DebtScorecardEvaluation | None]:
    """Evaluate scorecard budgets and return (violations, summary)."""
    now = today or date.today()
    inventory = build_exemption_inventory(registry_path, today=now)
    scorecard = load_debt_scorecard(scorecard_path)

    validation_errors = validate_debt_scorecard(scorecard_path)
    if validation_errors:
        return validation_errors, None

    baseline = scorecard["baseline"]
    baseline_total = int(baseline["total_exemptions"])

    target = _current_quarter_target(scorecard, today=now)
    if target is None:
        return [f"Missing quarterly target for current quarter '{_quarter_label(now)}'"], None

    active_windows = [
        window
        for window in scorecard.get("grace_windows", [])
        if _is_active_grace_window(window, today=now)
    ]
    typed_active_windows = [window for window in active_windows if isinstance(window, dict)]
    allowance_total, allowance_by_registry, allowance_by_group = _collect_allowances(
        typed_active_windows
    )

    target_registry_budgets = target["registry_budgets"]
    target_group_budgets = target["group_budgets"]
    by_group = _compute_group_counts(
        by_registry=inventory.by_registry,
        registry_groups=scorecard["registry_groups"],
    )
    violations = _evaluate_registry_budgets(
        by_registry=inventory.by_registry,
        target_registry_budgets=target_registry_budgets,
        allowance_by_registry=allowance_by_registry,
    )
    violations.extend(
        _evaluate_group_budgets(
            by_group=by_group,
            target_group_budgets=target_group_budgets,
            allowance_by_group=allowance_by_group,
        )
    )

    total_budget = int(target["max_total_exemptions"]) + allowance_total
    if inventory.total_exemptions > total_budget:
        violations.append(
            f"total exemptions {inventory.total_exemptions} exceeds budget {total_budget}"
        )

    score = compute_integral_debt_score(
        total_exemptions=inventory.total_exemptions,
        expired_entries=inventory.expired_entries,
        baseline_total=baseline_total,
    )
    min_score = float(target["min_integral_score"])
    if score < min_score:
        violations.append(f"integral debt score {score} is below target {min_score}")

    summary = DebtScorecardEvaluation(
        quarter=str(target["quarter"]),
        integral_score=score,
        total_exemptions=inventory.total_exemptions,
        total_budget=total_budget,
        active_grace_windows=tuple(
            str(window.get("rf_id", "<unknown>")) for window in active_windows
        ),
        by_registry=dict(inventory.by_registry),
        by_group=by_group,
        by_owner=dict(inventory.by_owner),
        by_expiry_quarter=dict(inventory.by_expiry_quarter),
        expired_entries=inventory.expired_entries,
    )
    return violations, summary


__all__ = [
    "DebtScorecardEvaluation",
    "ExemptionInventory",
    "build_exemption_inventory",
    "compute_integral_debt_score",
    "evaluate_debt_scorecard",
    "load_debt_scorecard",
    "validate_debt_scorecard",
]
