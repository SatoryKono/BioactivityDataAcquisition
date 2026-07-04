"""Sub-service for debt scorecard and exemption-registry sync checks."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality.inventory import ExemptionInventorySummary

__all__ = ["validate_registry_sync"]


def _resolve_sync_baseline_section(
    scorecard: JsonDict,
) -> tuple[str, dict[str, object] | None]:
    """Resolve which scorecard baseline section governs live registry sync."""
    governance = scorecard.get("governance", {})
    section_name = "baseline"
    if isinstance(governance, dict):
        baseline_policy = governance.get("baseline_policy", {})
        if isinstance(baseline_policy, dict):
            configured = baseline_policy.get("registry_sync_source")
            if isinstance(configured, str) and configured.strip():
                section_name = configured.strip()
    section = scorecard.get(section_name)
    return section_name, section if isinstance(section, dict) else None


def _validate_registry_membership(
    *,
    live_names: set[str],
    baseline_names: set[str],
) -> list[str]:
    errors: list[str] = []
    missing_in_scorecard = sorted(live_names - baseline_names)
    if missing_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry missing live registries: "
            f"{missing_in_scorecard}"
        )

    stale_in_scorecard = sorted(baseline_names - live_names)
    if stale_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry has stale registries not present in "
            f"exemptions YAML: {stale_in_scorecard}"
        )
    return errors


def _validate_registry_baselines(
    *,
    baseline_by_registry: dict[str, object],
    inventory: ExemptionInventorySummary,
    comparable_registries: list[str],
) -> list[str]:
    errors: list[str] = []
    for registry_name in comparable_registries:
        baseline_value = baseline_by_registry.get(registry_name)
        if not isinstance(baseline_value, int):
            errors.append(
                "scorecard.baseline.by_registry."
                f"{registry_name}: expected int, got {type(baseline_value).__name__}"
            )
            continue
        live_count = inventory.by_registry.get(registry_name, 0)
        if live_count > baseline_value:
            errors.append(
                f"registry '{registry_name}' live count {live_count} exceeds "
                f"scorecard baseline {baseline_value}"
            )
    return errors


def _validate_total_exemptions(
    *,
    baseline: dict[str, object],
    inventory: ExemptionInventorySummary,
) -> list[str]:
    baseline_total = baseline.get("total_exemptions")
    if not isinstance(baseline_total, int):
        return [
            "scorecard.baseline.total_exemptions: expected int, "
            f"got {type(baseline_total).__name__}"
        ]
    if inventory.total_exemptions > baseline_total:
        return [
            f"live total_exemptions {inventory.total_exemptions} exceeds "
            f"scorecard baseline {baseline_total}"
        ]
    return []


def validate_registry_sync(
    *,
    raw_registry: JsonDict,
    scorecard: JsonDict,
    inventory: ExemptionInventorySummary,
) -> list[str]:
    """Validate scorecard baseline synchronization with live registry inventory."""
    raw_registries = raw_registry.get("registries", {})
    if not isinstance(raw_registries, dict):
        return ["exemptions.registries: expected mapping"]

    baseline_section_name, baseline = _resolve_sync_baseline_section(scorecard)
    if baseline is None:
        return [f"scorecard.{baseline_section_name}: expected mapping"]

    baseline_by_registry = baseline.get("by_registry", {})
    if not isinstance(baseline_by_registry, dict):
        return [f"scorecard.{baseline_section_name}.by_registry: expected mapping"]

    errors: list[str] = []
    inventory_registry_names = set(raw_registries)
    baseline_registry_names = set(baseline_by_registry)

    errors.extend(
        _validate_registry_membership(
            live_names=inventory_registry_names,
            baseline_names=baseline_registry_names,
        )
    )

    comparable_registries = sorted(inventory_registry_names & baseline_registry_names)
    errors.extend(
        _validate_registry_baselines(
            baseline_by_registry=baseline_by_registry,
            inventory=inventory,
            comparable_registries=comparable_registries,
        )
    )
    errors.extend(_validate_total_exemptions(baseline=baseline, inventory=inventory))

    return errors
