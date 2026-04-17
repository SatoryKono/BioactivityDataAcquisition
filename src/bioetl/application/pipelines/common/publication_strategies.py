"""Default implementations for Publication Strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import (
    IdentifierResolverStrategy,
    PublicationMetadataStrategy,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import JsonDict


class DefaultIdentifierResolver(IdentifierResolverStrategy):
    """Default identifier resolver that checks for a specific field."""

    def __init__(self, primary_id_field: str):
        self._primary_id_field = primary_id_field

    def get_primary_id_field(self) -> str:
        """Return the configured primary-id field for publication records."""
        return self._primary_id_field

    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> (
        tuple[str, Any] | None
    ):  # Any: primary ID values remain provider-specific scalars at the strategy seam.
        """Validate primary-id presence and return the `(field, value)` pair."""
        primary_id = business_data.get(self._primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None
        return self._primary_id_field, primary_id


class DefaultPublicationMetadataPolicy(PublicationMetadataStrategy):
    """Default metadata strategy."""

    def __init__(
        self,
        entity_class: type[BaseEntity],
        log_fallback: bool = True,
    ):
        self._entity_class = entity_class
        self._log_fallback = log_fallback

    def get_entity_class(self) -> type[BaseEntity]:
        """Return the entity class used to inflate publication domain records."""
        return self._entity_class

    def should_log_fallback_lookup(self) -> bool:
        """Return whether fallback lookup events should be logged."""
        return self._log_fallback

    def post_process_silver_record(self, silver_record: JsonDict) -> JsonDict:
        """Return silver record as-is by default."""
        return silver_record
