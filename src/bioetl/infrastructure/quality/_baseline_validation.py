"""Baseline, historical snapshot, and registry-groups validators."""

from __future__ import annotations

from collections import Counter

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _validate_non_negative_int,
)


def _validate_registry_counts_mapping(
    *,
    field_name: str,
    raw_mapping: object,
    errors: list[str],
) -> dict[str, int] | None:
    """Validate a registry-count mapping and return normalized counts."""
    if not isinstance(raw_mapping, dict) or not raw_mapping:
        errors.append(f"{field_name}: required non-empty mapping")
        return None

    normalized_registry_counts: dict[str, int] = {}
    for registry_name, count in sorted(raw_mapping.items()):
        if not isinstance(registry_name, str) or not registry_name.strip():
            errors.append(f"{field_name}: registry name must be non-empty string")
            continue
        parsed = _validate_non_negative_int(
            count,
            field_name=f"{field_name}.{registry_name}",
            errors=errors,
        )
        if parsed is not None:
            normalized_registry_counts[registry_name] = parsed

    return normalized_registry_counts


def _validate_baseline_mapping(
    *,
    field_name: str,
    baseline: object,
    errors: list[str],
) -> tuple[int | None, dict[str, int]] | None:
    """Validate one baseline-like mapping with total and by-registry counts."""
    if not isinstance(baseline, dict):
        errors.append(f"{field_name}: required mapping")
        return None

    baseline_total = _validate_non_negative_int(
        baseline.get("total_exemptions"),
        field_name=f"{field_name}.total_exemptions",
        errors=errors,
    )
    normalized_registry_counts = _validate_registry_counts_mapping(
        field_name=f"{field_name}.by_registry",
        raw_mapping=baseline.get("by_registry"),
        errors=errors,
    )
    if normalized_registry_counts is None:
        return None

    if baseline_total is not None and baseline_total != sum(
        normalized_registry_counts.values()
    ):
        errors.append(
            f"{field_name}.total_exemptions must equal sum({field_name}.by_registry.*)"
        )

    return baseline_total, normalized_registry_counts


def _validate_baseline_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    errors: list[str],
) -> tuple[int | None, dict[str, int]] | None:
    return _validate_baseline_mapping(
        field_name="baseline",
        baseline=raw.get("baseline"),
        errors=errors,
    )


def _validate_historical_baseline_section(
    raw: JsonDict,
    *,
    enforceable_total: int | None,
    enforceable_registry_counts: dict[str, int],
    errors: list[str],
) -> tuple[int | None, dict[str, int]] | None:
    """Validate frozen historical baseline and its relation to enforceable baseline."""
    historical = raw.get("historical_baseline")
    result = _validate_baseline_mapping(
        field_name="historical_baseline",
        baseline=historical,
        errors=errors,
    )
    if result is None:
        return None

    if not isinstance(historical, dict):
        return None

    _validate_historical_baseline_metadata(historical=historical, errors=errors)

    historical_total, historical_registry_counts = result
    _validate_historical_registry_coverage(
        enforceable_registry_counts=enforceable_registry_counts,
        historical_registry_counts=historical_registry_counts,
        errors=errors,
    )
    _validate_historical_total_floor(
        historical_total=historical_total,
        enforceable_total=enforceable_total,
        errors=errors,
    )
    _validate_historical_registry_floors(
        enforceable_registry_counts=enforceable_registry_counts,
        historical_registry_counts=historical_registry_counts,
        errors=errors,
    )
    return result


def _validate_historical_baseline_metadata(
    *,
    historical: JsonDict,
    errors: list[str],
) -> None:
    """Validate historical baseline metadata fields."""
    if _parse_iso_date(historical.get("snapshot_date")) is None:
        errors.append(
            "historical_baseline.snapshot_date: expected ISO date (YYYY-MM-DD)"
        )
    source_report = historical.get("source_report")
    if not isinstance(source_report, str) or not source_report.strip():
        errors.append("historical_baseline.source_report: expected non-empty string")


def _validate_historical_registry_coverage(
    *,
    enforceable_registry_counts: dict[str, int],
    historical_registry_counts: dict[str, int],
    errors: list[str],
) -> None:
    """Validate registry-set parity between baseline and historical baseline."""
    enforceable_registry_names = set(enforceable_registry_counts)
    historical_registry_names = set(historical_registry_counts)

    missing_registries = sorted(enforceable_registry_names - historical_registry_names)
    extra_registries = sorted(historical_registry_names - enforceable_registry_names)
    if missing_registries:
        errors.append(
            "historical_baseline.by_registry missing enforceable registries: "
            f"{missing_registries}"
        )
    if extra_registries:
        errors.append(
            "historical_baseline.by_registry has registries not present in baseline: "
            f"{extra_registries}"
        )


def _validate_historical_total_floor(
    *,
    historical_total: int | None,
    enforceable_total: int | None,
    errors: list[str],
) -> None:
    """Validate historical total does not fall below enforceable baseline."""
    if (
        historical_total is not None
        and enforceable_total is not None
        and historical_total < enforceable_total
    ):
        errors.append(
            "historical_baseline.total_exemptions must be greater than or equal to "
            "baseline.total_exemptions"
        )


def _validate_historical_registry_floors(
    *,
    enforceable_registry_counts: dict[str, int],
    historical_registry_counts: dict[str, int],
    errors: list[str],
) -> None:
    """Validate historical registry counts do not fall below baseline counts."""
    for registry_name, enforceable_count in sorted(enforceable_registry_counts.items()):
        historical_count = historical_registry_counts.get(registry_name)
        if historical_count is not None and historical_count < enforceable_count:
            errors.append(
                "historical_baseline.by_registry."
                f"{registry_name} must be greater than or equal to "
                f"baseline.by_registry.{registry_name}"
            )


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


def _validate_grouped_registry_coverage(
    grouped_registries: list[str],
    baseline_registry_names: set[str],
    errors: list[str],
) -> None:
    """Validate no duplicates, no missing, no extras in grouped registries."""
    grouped_counter = Counter(grouped_registries)
    duplicates = sorted(name for name, count in grouped_counter.items() if count > 1)
    if duplicates:
        errors.append(
            f"registry_groups: registries listed in multiple groups: {duplicates}"
        )

    grouped_names = set(grouped_counter)
    missing = sorted(baseline_registry_names - grouped_names)
    extra = sorted(grouped_names - baseline_registry_names)
    if missing:
        errors.append(f"registry_groups: missing baseline registries {missing}")
    if extra:
        errors.append(f"registry_groups: unknown registries {extra}")


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

    normalized_groups, grouped_registries = _normalize_registry_groups(
        registry_groups=registry_groups,
        errors=errors,
    )
    _validate_grouped_registry_coverage(
        grouped_registries, baseline_registry_names, errors
    )
    return normalized_groups


def _normalize_registry_groups(
    *,
    registry_groups: dict[object, object],
    errors: list[str],
) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    """Normalize registry group mappings and collect listed registries."""
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
    return normalized_groups, grouped_registries


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
