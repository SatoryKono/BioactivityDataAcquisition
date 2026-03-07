"""Publication registry models."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["PublicationMapping"]


@dataclass(frozen=True, slots=True)
class PublicationMapping:
    """Immutable mapping from canonical publication entity to ChEMBL API details."""

    canonical_name: str
    api_resource: str
    plural_key: str
    primary_key_field: str
    primary_key_fields: tuple[str, ...] | None = None
    is_legacy_alias: bool = False

    def get_dedup_key_fields(self) -> tuple[str, ...]:
        """Get the fields to use for deduplication."""
        if self.primary_key_fields is not None:
            return self.primary_key_fields
        return (self.primary_key_field,)
