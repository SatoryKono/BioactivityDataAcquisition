"""Contracts for filter enrichment."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FilterEnricherABC(Protocol):
    """Interface for enriching API filters with domain defaults.

    This is an application-layer concern that should not be implemented
    in infrastructure. Infrastructure services should accept a filter
    enricher via dependency injection.
    """

    def enrich_filters(
        self, entity: str, filters: dict[str, object]
    ) -> dict[str, object]:
        """Enrich filters with domain-specific defaults.

        Args:
            entity: The entity name (e.g., 'assay', 'activity').
            filters: Original filter dict.

        Returns:
            Enriched filter dict (may be same or new dict).
        """
        ...
