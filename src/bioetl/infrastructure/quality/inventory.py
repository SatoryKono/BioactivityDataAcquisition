"""Exemption inventory aggregation for debt scorecard governance."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bioetl.infrastructure.quality._primitives import _parse_iso_date, _quarter_label
from bioetl.infrastructure.quality.exemptions_registry import load_exemptions_registry


@dataclass(frozen=True)
class ExemptionInventory:
    """Aggregated exemption inventory for governance calculations."""

    total_exemptions: int
    by_registry: dict[str, int]
    by_owner: dict[str, int]
    by_expiry_quarter: dict[str, int]
    expired_entries: int


def build_exemption_inventory(
    registry_path: Path | str | None = None,
    *,
    today: date | None = None,
) -> ExemptionInventory:
    """Build aggregated inventory from the exemptions registry.

    Returns:
        ExemptionInventory with aggregated counts by registry, owner, expiry quarter, and expired entries.
    """
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
            owner_name = (
                owner.strip()
                if isinstance(owner, str) and owner.strip()
                else "<missing>"
            )
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


__all__ = [
    "ExemptionInventory",
    "build_exemption_inventory",
]
