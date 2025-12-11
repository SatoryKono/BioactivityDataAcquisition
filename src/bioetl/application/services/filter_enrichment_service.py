"""Filter enrichment service for adding domain-specific defaults to API filters."""

from __future__ import annotations

from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC


class FilterEnrichmentService(FilterEnricherABC):
    """Enriches API filters with domain-specific defaults.

    This service encapsulates the business logic for adding default fields
    and other domain-specific parameters to API filters. This logic belongs
    in the application layer, not infrastructure.

    Example:
        >>> provider = ApplicationFieldProvider()
        >>> enricher = FilterEnrichmentService(provider)
        >>> filters = enricher.enrich_filters("assay", {"limit": 100})
        >>> # filters now includes "fields" key with default assay fields
    """

    def __init__(
        self,
        field_provider: DefaultFieldProviderABC | None = None,
    ) -> None:
        """Initialize the filter enrichment service.

        Args:
            field_provider: Optional provider for entity default fields.
        """
        self._field_provider = field_provider

    def enrich_filters(
        self, entity: str, filters: dict[str, object]
    ) -> dict[str, object]:
        """Enrich filters with domain-specific defaults.

        Adds default fields for the entity if a field provider is configured
        and the filters don't already specify fields.

        Args:
            entity: The entity name (e.g., 'assay', 'activity').
            filters: Original filter dict.

        Returns:
            Enriched filter dict with default fields added if applicable.
        """
        if self._field_provider is None:
            return filters

        # Skip if fields already specified
        if "fields" in filters:
            return filters

        fields = self._field_provider.get_default_fields(entity)
        if fields:
            return {**filters, "fields": ",".join(fields)}

        return filters


class NullFilterEnricher(FilterEnricherABC):
    """No-op filter enricher that passes filters through unchanged.

    Used when no enrichment is needed or as a default/fallback.
    """

    def enrich_filters(
        self, entity: str, filters: dict[str, object]
    ) -> dict[str, object]:
        """Return filters unchanged."""
        return filters
