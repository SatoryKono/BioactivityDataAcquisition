"""Baseline and registry groups section validators."""

from __future__ import annotations

from collections import Counter

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import _validate_non_negative_int


def _validate_baseline_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
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
    raw: JsonDict,  # Any: YAML values are heterogeneous
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
