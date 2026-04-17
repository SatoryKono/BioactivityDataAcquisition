"""Publication Strategy interfaces for decomposing BasePublicationTransformer.

These interfaces define the isolated strategies for extracting business data
and resolving primary identifiers, reducing the risk of God Objects in
the publication transformation flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, JsonDict


@runtime_checkable
class DataExtractorStrategy(Protocol):
    """Strategy for extracting business data from a raw record."""

    def pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Optional pre-extraction validation hook.

        Raises:
            ValueError: If validation fails.
        """
        ...

    def extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract and normalize fields from bronze record."""
        ...


@runtime_checkable
class IdentifierResolverStrategy(Protocol):
    """Strategy for resolving and validating primary identifiers."""

    def get_primary_id_field(self) -> str:
        """Return the name of the primary identifier field."""
        ...

    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, Any] | None:  # Any: primary ID values remain provider-specific scalars across providers.
        """Validate primary ID presence.

        Returns:
            Tuple of (field_name, value) if valid, None if missing.
        """
        ...


@runtime_checkable
class PublicationMetadataStrategy(Protocol):
    """Strategy for publication metadata and entity instantiation."""

    def get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for this publication type."""
        ...

    def should_log_fallback_lookup(self) -> bool:
        """Return True if fallback lookup logging is enabled."""
        ...

    def post_process_silver_record(self, silver_record: JsonDict) -> JsonDict:
        """Apply provider-specific cleanup to the final Silver record."""
        ...
