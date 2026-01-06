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
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BasePublicationTransformer(BaseTransformer):
    """Abstract base class for publication transformers.

    Implements Template Method pattern for unified publication transformation:
    1. Pre-extraction validation (optional hook)
    2. Extract business data (_extract_business_data - abstract)
    3. Validate primary ID exists
    4. Log fallback lookup usage if applicable
    5. Generate entity ID
    6. Compute content hash (excluding metadata fields)
    7. Create domain entity (_get_entity_class - abstract)
    8. Convert to SilverRecord

    Subclasses MUST implement:
    - _extract_business_data(): Extract and normalize fields from record
    - _get_primary_id_field(): Return primary ID field name (e.g., 'openalex_id')
    - _get_entity_class(): Return the domain entity class

    Subclasses MAY override:
    - _pre_extract_validation(): Add validation before extraction
    - _should_log_fallback_lookup(): Disable fallback logging (default: True)
    """

    @abstractmethod
    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract and normalize fields from bronze record.

        Provider-specific extraction logic. Delegates to extractors module.

        Args:
            record: Raw Bronze record from provider API.

        Returns:
            Dictionary of extracted and normalized fields.

        """
        ...

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

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Unified publication transformation flow (Template Method).

        Orchestrates the transformation process:
        1. Pre-extraction validation (optional hook)
        2. Extract business data
        3. Validate primary ID exists
        4. Log fallback usage if applicable
        5. Generate entity ID
        6. Compute content hash
        7. Create domain entity
        8. Convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from provider API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Pre-extraction validation hook
        self._pre_extract_validation(context, record, index)

        # 2. Extract business data
        business_data = self._extract_business_data(record)

        # 3. Validate primary ID
        primary_id_field = self._get_primary_id_field()
        primary_id = business_data.get(primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None

        # 4. Log fallback usage if applicable
        if self._should_log_fallback_lookup():
            lookup_method = business_data.get("_lookup_method", "unknown")
            if lookup_method in ("title_fallback", "title_only"):
                context.logger.info(
                    "fallback_lookup_used",
                    **{primary_id_field: primary_id},
                    lookup_method=lookup_method,
                    original_doi=business_data.get("_original_doi"),
                )

        # 5. Generate entity ID
        entity_id = self.compute_entity_id(
            source_id=primary_id,
            record={primary_id_field: primary_id},
        )

        # 6. Compute content hash (exclude metadata fields)
        hash_data = {k: v for k, v in business_data.items() if not k.startswith("_")}
        content_hash = self.compute_content_hash(hash_data, exclude_none=True)

        # 7. Create domain entity
        entity = self._create_entity(
            self._get_entity_class(),
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 8. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))
