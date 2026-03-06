"""Query and header helpers for CrossRef adapter flows."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CROSSREF_SUPPORTED_ENTITY_TYPES",
    "CrossRefQueryBuilder",
    "resolve_filter_field",
    "validate_crossref_entity_type",
]

CROSSREF_SUPPORTED_ENTITY_TYPES = frozenset(("work", "publication"))


def validate_crossref_entity_type(entity_type: str) -> None:
    """Validate CrossRef entity type for fetch/filter operations."""
    if entity_type in CROSSREF_SUPPORTED_ENTITY_TYPES:
        return
    raise ValueError(
        f"CrossRefAdapter supports 'work' or 'publication', got: {entity_type}"
    )


def resolve_filter_field(filter_field: str | None) -> str:
    """Return effective filter field value for CrossRef flow.

    Returns:
        Filter field string, defaulting to "doi" if None is provided.
    """
    return filter_field or "doi"


@dataclass(frozen=True, slots=True)
class CrossRefQueryBuilder:
    """Build request headers and static query fragments for CrossRef."""

    api_base: str
    mailto: str

    def build_headers(self) -> dict[str, str]:
        """Build request headers with polite-pool mailto identification.

        Returns:
            Dictionary of HTTP headers with User-Agent and Accept fields.
        """
        return {
            "User-Agent": f"BioETL/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

    def build_health_probe_url(self) -> str:
        """Build health probe URL.

        Returns:
            Full URL string for the CrossRef health probe endpoint.
        """
        return f"{self.api_base}/works"

    def build_health_probe_params(self) -> dict[str, str]:
        """Build health probe query parameters.

        Returns:
            Dictionary of query parameters for the health probe request.
        """
        return {
            "rows": "1",
            "mailto": self.mailto,
        }
