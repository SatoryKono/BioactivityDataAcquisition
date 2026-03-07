"""Sub-service for debt scorecard and exemption-registry sync checks."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality.inventory import ExemptionInventory

__all__ = ["validate_registry_sync"]


def validate_registry_sync(
    *,
    raw_registry: JsonDict,
    scorecard: JsonDict,
    inventory: ExemptionInventory,
) -> list[str]:
    """Validate scorecard baseline synchronization with live registry inventory."""
    raw_registries = raw_registry.get("registries", {})
    if not isinstance(raw_registries, dict):
        return ["exemptions.registries: expected mapping"]

    baseline = scorecard.get("baseline", {})
    if not isinstance(baseline, dict):
        return ["scorecard.baseline: expected mapping"]

    baseline_by_registry = baseline.get("by_registry", {})
    if not isinstance(baseline_by_registry, dict):
        return ["scorecard.baseline.by_registry: expected mapping"]

    errors: list[str] = []
    inventory_registry_names = set(raw_registries)
    baseline_registry_names = set(baseline_by_registry)

    missing_in_scorecard = sorted(inventory_registry_names - baseline_registry_names)
    if missing_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry missing live registries: "
            f"{missing_in_scorecard}"
        )

    stale_in_scorecard = sorted(baseline_registry_names - inventory_registry_names)
    if stale_in_scorecard:
        errors.append(
            "scorecard.baseline.by_registry has stale registries not present in "
            f"exemptions YAML: {stale_in_scorecard}"
        )

    comparable_registries = sorted(inventory_registry_names & baseline_registry_names)
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

    baseline_total = baseline.get("total_exemptions")
    if not isinstance(baseline_total, int):
        errors.append(
            "scorecard.baseline.total_exemptions: expected int, "
            f"got {type(baseline_total).__name__}"
        )
    elif inventory.total_exemptions > baseline_total:
        errors.append(
            f"live total_exemptions {inventory.total_exemptions} exceeds "
            f"scorecard baseline {baseline_total}"
        )

    return errors
