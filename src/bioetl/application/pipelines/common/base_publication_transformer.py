"""Base Publication Transformer with Template Method pattern.

Provides common transformation flow for publication entities from
different providers (OpenAlex, SemanticScholar, CrossRef).

Reduces code duplication by extracting shared logic:
- Business data extraction orchestration
- Primary ID validation
- Fallback lookup logging
- Entity ID and content hash computation
- Domain entity creation and Silver record conversion
"""

from __future__ import annotations

from abc import abstractmethod
from functools import partial

from bioetl.domain.types import JsonDict

__all__ = ["BasePublicationTransformer"]


from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.common.publication_blocks import ExtractionBlock
from bioetl.domain.mapping.publication_type_classification import (
    classify_publication_type,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BasePublicationTransformer(BaseTransformer):
    """Shared Template Method flow for publication transformers."""

    def __init__(
        self,
        provider: str,
        entity_type: str = "publication",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize publication transformer with explicit DI seams."""
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
        )

    @property
    def extraction_blocks(self) -> list[ExtractionBlock]:
        """Optional list of declarative blocks to extract data.

        Subclasses can override this to use the block architecture instead
        of overriding _extract_business_data manually.
        """
        return []

    def _extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract and normalize fields from bronze record.

        Provider-specific extraction logic. Delegates to extraction_blocks if provided.

        Args:
            record: Raw Bronze record from provider API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        blocks = self.extraction_blocks
        if blocks:
            result: JsonDict = {}
            for block in blocks:
                result.update(block.extract(record))
            return result

        raise NotImplementedError(
            f"{self.__class__.__name__} must implement extraction_blocks property "
            "or override _extract_business_data() method."
        )

    @abstractmethod
    def _get_primary_id_field(self) -> str:
        """Return the name of the primary identifier field.

        Examples:
        - OpenAlex: 'openalex_id'
        - SemanticScholar: 'paper_id'
        - CrossRef: 'doi'

        Returns:
            Field name used as primary identifier in business_data.

        """
        ...

    @abstractmethod
    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for this publication type.

        Returns:
            Domain entity class (e.g., OpenAlexPublicationEntity).

        """
        ...

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Optional pre-extraction validation hook.

        Override to add validation before business data extraction.
        Raise ValueError to skip the record with validation error logging.

        Default implementation does nothing.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from provider API.
            index: Sequential index of the record in the pipeline run.

        Raises:
            ValueError: If validation fails (caught by BaseTransformer.transform).

        """

    def _should_log_fallback_lookup(self) -> bool:
        """Return True if fallback lookup logging is enabled.

        Override to disable for providers without lookup metadata
        (e.g., CrossRef which uses DOI-only lookup).

        Returns:
            True to log fallback usage, False to skip.

        """
        return True

    _CONTENT_FIELDS: tuple[str, ...] = ("abstract",)
    """Fields to normalize via ``strip_html_tags`` after extraction."""

    def _normalize_content_fields(
        self,
        business_data: dict[
            str, Any  # Any: transformer record has heterogeneous values
        ],  # Any: transformer record has heterogeneous values
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Apply uniform content normalization to text fields.

        Strips residual HTML/XML tags from abstract (and other fields
        listed in ``_CONTENT_FIELDS``).
        The operation is idempotent — safe for providers that already
        clean these fields in ``_extract_business_data``.

        Subclasses MAY override to customize or extend normalization.

        Args:
            business_data: Extracted business data dictionary (mutated in-place).

        Returns:
            The same dictionary with content fields normalized.

        """
        for field in self._CONTENT_FIELDS:
            raw = business_data.get(field)
            if raw is not None:
                business_data[field] = self._data_normalizer.strip_html_tags(raw)
        return business_data

    def _validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, Any] | None:  # Any: PK value type varies by provider
        """Validate primary ID presence.

        Returns:
            Tuple of (field_name, value) if valid, None if missing.

        """
        primary_id_field = self._get_primary_id_field()
        primary_id = business_data.get(primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None
        return primary_id_field, primary_id

    def _log_fallback_if_needed(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        primary_id_field: str,
        primary_id: Any,  # Any: heterogeneous ID types across providers
    ) -> None:
        """Log fallback lookup usage when applicable."""
        if self._should_log_fallback_lookup():
            lookup_method = business_data.get("_lookup_method", "unknown")
            if lookup_method in ("title_fallback", "title_only"):
                context.logger.info(
                    "fallback_lookup_used",
                    **{primary_id_field: primary_id},
                    lookup_method=lookup_method,
                    original_id=business_data.get("_original_id"),
                )

    def _compute_identifiers(
        self,
        primary_id_field: str,
        primary_id: Any,  # Any: heterogeneous ID types across providers
        business_data: JsonDict,
    ) -> tuple[str, str]:
        """Compute entity_id and content_hash.

        Returns:
            Tuple of (entity_id, content_hash).

        """
        entity_id = self.compute_entity_id(
            source_id=primary_id,
            record={primary_id_field: primary_id},
        )
        hash_data = {k: v for k, v in business_data.items() if not k.startswith("_")}
        content_hash = self.compute_content_hash(hash_data, exclude_none=True)
        return entity_id, content_hash

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate publication payload for application finalization."""
        prepared = _prepare_publication_business_data(self, context, record, index)
        if prepared is None:
            return None
        primary_id_field, primary_id, business_data = prepared
        entity_id = self.compute_entity_id(
            source_id=primary_id,
            record={primary_id_field: primary_id},
        )
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=business_data,
            build_silver_record=partial(
                _build_publication_silver_record,
                self,
            ),
            apply_structural_policy=self._apply_structural_policy,
            apply_silver_filter=self._apply_silver_filter,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Unified publication transformation flow (Template Method)."""
        prepared = _prepare_publication_business_data(self, context, record, index)
        if prepared is None:
            return None
        primary_id_field, primary_id, business_data = prepared
        normalized_business_data = _normalize_publication_business_data(
            self,
            business_data,
        )
        entity_id, content_hash = self._compute_identifiers(
            primary_id_field, primary_id, normalized_business_data
        )

        return _build_publication_silver_record(
            self,
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )

    def _classify_publication_type(
        self,
        provider: str,
        raw_type: str | None = None,
        raw_types_list: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Classify publication type using the unified 3-level hierarchy.

        Delegates to domain classification module.

        Args:
            provider: Provider name ("openalex", "crossref", "pubmed", "semanticscholar").
            raw_type: Single raw type string (for OpenAlex / CrossRef).
            raw_types_list: List of raw type strings (for PubMed / S2).

        Returns:
            Dict with keys publication_type_unified, publication_subclass,
            publication_class (all str | None).

        """
        entry = classify_publication_type(
            provider, raw_type=raw_type, raw_types_list=raw_types_list
        )
        if entry is None:
            return {
                "publication_type_unified": None,
                "publication_subclass": None,
                "publication_class": None,
            }
        return {
            "publication_type_unified": entry.unified_type,
            "publication_subclass": entry.subclass,
            "publication_class": entry.class_code,
        }

def _prepare_publication_business_data(
    transformer: BasePublicationTransformer,
    context: PipelineContext,
    record: BronzeRecord,
    index: int,
) -> tuple[str, object, JsonDict] | None:
    """Prepare publication business data and validate the primary identifier."""
    transformer._pre_extract_validation(context, record, index)
    business_data = transformer._extract_business_data(record)
    transformer._normalize_content_fields(business_data)

    id_result = transformer._validate_primary_id(context, business_data, index)
    if id_result is None:
        return None
    primary_id_field, primary_id = id_result
    transformer._log_fallback_if_needed(
        context,
        business_data,
        primary_id_field,
        primary_id,
    )
    return primary_id_field, primary_id, business_data


def _normalize_publication_business_data(
    transformer: BasePublicationTransformer,
    business_data: JsonDict,
) -> JsonDict:
    """Normalize publication business data before legacy hash finalization."""
    normalized = RecordNormalizationProcessor(
        provider=transformer.provider,
    ).normalize_business_data(business_data)
    if isinstance(business_data.get("issn"), list):
        normalized["issn"] = list(business_data["issn"])
    return normalized


def _build_publication_silver_record(
    transformer: BasePublicationTransformer,
    context: PipelineContext,
    entity_id: str,
    content_hash: str,
    index: int,
    business_data: JsonDict,
) -> SilverRecord:
    """Build a finalized Silver record from normalized publication business data."""
    entity = transformer._create_entity(
        transformer._get_entity_class(),
        context,
        entity_id=entity_id,
        content_hash=content_hash,
        index=index,
        **business_data,
    )
    return cast("SilverRecord", transformer.entity_to_silver_record(entity))
