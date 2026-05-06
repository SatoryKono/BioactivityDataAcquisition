"""Assembly helpers for publication transformer runtime flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, JsonDict, PrimaryId, SilverRecord


class _PublicationDataExtractor(Protocol):
    def pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None: ...

    def extract_business_data(self, record: BronzeRecord) -> JsonDict: ...


class _PublicationIdentifierResolver(Protocol):
    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, PrimaryId] | None: ...


class _PublicationMetadataStrategy(Protocol):
    def get_entity_class(self) -> type[BaseEntity]: ...

    def post_process_silver_record(
        self,
        silver_record: SilverRecord,
    ) -> SilverRecord: ...


class _PublicationRecordNormalizer(Protocol):
    def normalize_business_data(self, business_data: JsonDict) -> JsonDict: ...


class _SupportsPublicationBusinessNormalization(Protocol):
    _record_normalizer: _PublicationRecordNormalizer


class PublicationAssemblyTransformer(Protocol):
    """Structural protocol for publication assembly helper functions."""

    _data_extractor: _PublicationDataExtractor
    _identifier_resolver: _PublicationIdentifierResolver
    _metadata_strategy: _PublicationMetadataStrategy
    _record_normalizer: _PublicationRecordNormalizer

    def _normalize_content_fields(
        self,
        business_data: JsonDict,
    ) -> JsonDict: ...

    def _log_fallback_if_needed(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        primary_id_field: str,
        primary_id: PrimaryId,
    ) -> None: ...

    def _create_entity(
        self,
        entity_class: type[BaseEntity],
        context: PipelineContext,
        **kwargs: object,
    ) -> BaseEntity: ...

    def entity_to_silver_record(self, entity: BaseEntity) -> SilverRecord:
        """Project a domain entity into a serializable Silver-layer record."""
        ...


@dataclass(frozen=True, slots=True)
class PreparedPublicationOutcome:
    """Typed seam shared by staged and legacy publication transformation flows."""

    primary_id_field: str
    primary_id: PrimaryId
    business_data: JsonDict


def prepare_publication_payload(
    transformer: PublicationAssemblyTransformer,
    context: PipelineContext,
    record: BronzeRecord,
    index: int,
) -> PreparedPublicationOutcome | None:
    """Prepare publication business data and validate the primary identifier."""
    transformer._data_extractor.pre_extract_validation(context, record, index)
    business_data = transformer._data_extractor.extract_business_data(record)
    transformer._normalize_content_fields(business_data)

    id_result = transformer._identifier_resolver.validate_primary_id(
        context,
        business_data,
        index,
    )
    if id_result is None:
        return None
    primary_id_field, primary_id = id_result

    transformer._log_fallback_if_needed(
        context,
        business_data,
        primary_id_field,
        primary_id,
    )
    return PreparedPublicationOutcome(
        primary_id_field=primary_id_field,
        primary_id=primary_id,
        business_data=business_data,
    )


def normalize_publication_business_data(
    transformer: _SupportsPublicationBusinessNormalization,
    business_data: JsonDict,
) -> JsonDict:
    """Normalize publication business data before legacy hash finalization."""
    return transformer._record_normalizer.normalize_business_data(business_data)


def build_publication_silver_record(
    transformer: PublicationAssemblyTransformer,
    context: PipelineContext,
    entity_id: str,
    content_hash: str,
    index: int,
    business_data: JsonDict,
) -> SilverRecord:
    """Build a finalized Silver record from normalized publication business data."""
    entity_class = transformer._metadata_strategy.get_entity_class()
    entity = transformer._create_entity(
        entity_class,
        context,
        entity_id=entity_id,
        content_hash=content_hash,
        index=index,
        **business_data,
    )
    silver_record = transformer.entity_to_silver_record(entity)
    return transformer._metadata_strategy.post_process_silver_record(silver_record)
