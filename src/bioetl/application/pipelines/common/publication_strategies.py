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
        return self._primary_id_field

    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, Any] | None:
        primary_id = business_data.get(self._primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None
        return self._primary_id_field, primary_id


class DefaultPublicationMetadata(PublicationMetadataStrategy):
    """Default metadata strategy."""

    def __init__(
        self,
        entity_class: type[BaseEntity],
        log_fallback: bool = True,
    ):
        self._entity_class = entity_class
        self._log_fallback = log_fallback

    def get_entity_class(self) -> type[BaseEntity]:
        return self._entity_class

    def should_log_fallback_lookup(self) -> bool:
        return self._log_fallback
