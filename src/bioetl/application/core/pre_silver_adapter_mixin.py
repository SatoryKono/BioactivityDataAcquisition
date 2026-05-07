"""Shared adapters for transformers that participate in staged PreSilver finalization."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import SilverRecord


class PreSilverAdapterMixin:
    """Adapt finalized Silver-record flows to the ``PreSilverRecord`` protocol."""

    entity_class: type[object]
    provider: str
    entity_type: str

    def _finalize_staged_business_data(
        self,
        *,
        context: PipelineContext,
        entity_id: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Normalize business data, compute hash, and project findings."""
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        content_hash = self.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = self._build_pre_silver_record(
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        return cast(
            JsonDict,
            normalizer.project_normalization_findings(
                cast(JsonDict, silver_record),
                context=context,
                index=index,
            ),
        )

    def _finalize_prepared_business_data(
        self,
        *,
        context: PipelineContext,
        source_id: str,
        identity_record: JsonDict,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Compute the entity id and finalize one prepared staged payload."""
        entity_id = self.compute_entity_id(
            source_id=source_id,
            record=identity_record,
        )
        return self._finalize_staged_business_data(
            context=context,
            entity_id=entity_id,
            index=index,
            business_data=business_data,
        )

    def _transform_prepared_business_data(
        self,
        *,
        context: PipelineContext,
        source_id: str,
        identity_record: JsonDict,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Finalize one prepared payload and return it as a Silver record."""
        return cast(
            "SilverRecord",
            self._finalize_prepared_business_data(
                context=context,
                source_id=source_id,
                identity_record=identity_record,
                index=index,
                business_data=business_data,
            ),
        )

    def _transform_identity_business_data(
        self,
        *,
        context: PipelineContext,
        source_id: str,
        identity_field: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Finalize one prepared payload with a single identity field."""
        return self._transform_prepared_business_data(
            context=context,
            source_id=source_id,
            identity_record={identity_field: source_id},
            index=index,
            business_data=business_data,
        )

    def _finalize_normalized_business_data(
        self,
        *,
        context: PipelineContext,
        index: int,
        business_data: JsonDict,
        resolve_entity_id: Callable[[JsonDict], str],
    ) -> JsonDict:
        """Normalize business data, derive a custom entity id, and finalize it."""
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        entity_id = resolve_entity_id(normalized_business_data)
        content_hash = self.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = self._build_pre_silver_record(
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        return cast(
            JsonDict,
            normalizer.project_normalization_findings(
                cast(JsonDict, silver_record),
                context=context,
                index=index,
            ),
        )

    def _transform_optional_normalized_business_data(
        self,
        *,
        context: PipelineContext,
        index: int,
        business_data: JsonDict | None,
        resolve_entity_id: Callable[[JsonDict], str],
    ) -> SilverRecord | None:
        """Finalize optional business data with a normalized custom entity id."""
        if business_data is None:
            return None
        return cast(
            "SilverRecord",
            self._finalize_normalized_business_data(
                context=context,
                index=index,
                business_data=business_data,
                resolve_entity_id=resolve_entity_id,
            ),
        )

    def _build_pre_silver_payload(
        self,
        *,
        entity_id: str,
        business_data: JsonDict,
    ) -> PreSilverRecord:
        """Build the staged ``PreSilverRecord`` payload from business data."""
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=business_data,
            build_silver_record=self._build_pre_silver_json_record,
            apply_structural_policy=self._apply_pre_silver_structural_policy,
            apply_silver_filter=self._apply_pre_silver_filter,
        )

    def _build_pre_silver_from_business_data(
        self,
        *,
        source_id: str,
        identity_record: JsonDict,
        business_data: JsonDict,
    ) -> PreSilverRecord:
        """Compute the entity id and package one prepared staged payload."""
        entity_id = self.compute_entity_id(
            source_id=source_id,
            record=identity_record,
        )
        return self._build_pre_silver_payload(
            entity_id=entity_id,
            business_data=business_data,
        )

    def _stage_prepared_business_data(
        self,
        *,
        source_id: str,
        identity_record: JsonDict,
        business_data: JsonDict,
    ) -> PreSilverRecord:
        """Stage one prepared payload as a PreSilver record."""
        return self._build_pre_silver_from_business_data(
            source_id=source_id,
            identity_record=identity_record,
            business_data=business_data,
        )

    def _stage_identity_business_data(
        self,
        *,
        source_id: str,
        identity_field: str,
        business_data: JsonDict,
    ) -> PreSilverRecord:
        """Stage one prepared payload with a single identity field."""
        return self._stage_prepared_business_data(
            source_id=source_id,
            identity_record={identity_field: source_id},
            business_data=business_data,
        )

    def _build_pre_silver_from_normalized_business_data(
        self,
        *,
        business_data: JsonDict,
        resolve_entity_id: Callable[[JsonDict], str],
    ) -> PreSilverRecord:
        """Normalize business data first, then stage it with a custom entity id."""
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        entity_id = resolve_entity_id(normalized_business_data)
        return self._build_pre_silver_payload(
            entity_id=entity_id,
            business_data=normalized_business_data,
        )

    def _stage_optional_normalized_business_data(
        self,
        *,
        business_data: JsonDict | None,
        resolve_entity_id: Callable[[JsonDict], str],
    ) -> PreSilverRecord | None:
        """Stage optional business data after normalized custom entity-id resolution."""
        if business_data is None:
            return None
        return self._build_pre_silver_from_normalized_business_data(
            business_data=business_data,
            resolve_entity_id=resolve_entity_id,
        )

    def _build_entity_backed_silver_record(
        self,
        *,
        entity_class: type[object],
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Create one entity-backed Silver record from normalized business data."""
        entity = self._create_entity(
            entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Build one default entity-backed finalized record for staged output."""
        silver_record = self._build_entity_backed_silver_record(
            entity_class=self.entity_class,
            context=context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            business_data=business_data,
        )
        return self._postprocess_pre_silver_record(
            silver_record,
            business_data=business_data,
        )

    def _postprocess_pre_silver_record(
        self,
        silver_record: SilverRecord,
        *,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Apply optional subclass post-processing to one finalized record."""
        del business_data
        return silver_record

    def _build_pre_silver_json_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Build a JSON-compatible finalized record for staged normalization."""
        return cast(
            JsonDict,
            self._build_pre_silver_record(
                context,
                entity_id,
                content_hash,
                index,
                business_data,
            ),
        )

    def _apply_pre_silver_structural_policy(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> JsonDict | None:
        """Adapt structural policy application to the ``PreSilverRecord`` protocol."""
        return cast(
            JsonDict | None,
            self._apply_structural_policy(
                context,
                cast("SilverRecord", record),
                index,
            ),
        )

    def _apply_pre_silver_filter(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> None:
        """Adapt Silver-filter application to the ``PreSilverRecord`` protocol."""
        self._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )
