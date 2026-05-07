"""Shared adapters for transformers that participate in staged PreSilver finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict, SilverRecord


class PreSilverAdapterMixin:
    """Adapt finalized Silver-record flows to the ``PreSilverRecord`` protocol."""

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
