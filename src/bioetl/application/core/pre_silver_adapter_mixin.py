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


class _PreSilverFinalizationFlowMixin:
    """Finalize staged business payloads into Silver-compatible records."""

    provider: str
    entity_type: str

    def _build_record_normalizer(self) -> RecordNormalizationProcessor:
        return RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )

    def _normalize_business_data(self, business_data: JsonDict) -> JsonDict:
        return self._build_record_normalizer().normalize_business_data(business_data)

    def _project_pre_silver_findings(
        self,
        silver_record: JsonDict,
        *,
        context: PipelineContext,
        index: int,
    ) -> JsonDict:
        return cast(
            JsonDict,
            self._build_record_normalizer().project_normalization_findings(
                silver_record,
                context=context,
                index=index,
            ),
        )

    def _finalize_staged_business_data(
        self,
        *,
        context: PipelineContext,
        entity_id: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        normalized_business_data = self._normalize_business_data(business_data)
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
        return self._project_pre_silver_findings(
            cast(JsonDict, silver_record),
            context=context,
            index=index,
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
        normalized_business_data = self._normalize_business_data(business_data)
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
        return self._project_pre_silver_findings(
            cast(JsonDict, silver_record),
            context=context,
            index=index,
        )

    def _transform_optional_normalized_business_data(
        self,
        *,
        context: PipelineContext,
        index: int,
        business_data: JsonDict | None,
        resolve_entity_id: Callable[[JsonDict], str],
    ) -> SilverRecord | None:
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


class _PreSilverStagingFlowMixin:
    """Stage business payloads behind the ``PreSilverRecord`` protocol."""

    def _build_pre_silver_payload(
        self,
        *,
        entity_id: str,
        business_data: JsonDict,
    ) -> PreSilverRecord:
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
        normalized_business_data = self._normalize_business_data(business_data)
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
        if business_data is None:
            return None
        return self._build_pre_silver_from_normalized_business_data(
            business_data=business_data,
            resolve_entity_id=resolve_entity_id,
        )


class _PreSilverRecordAdapterMixin:
    """Build entity-backed records and adapt Silver hooks to JSON payloads."""

    entity_class: type[object]

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
        self._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )


class PreSilverAdapterMixin(
    _PreSilverFinalizationFlowMixin,
    _PreSilverStagingFlowMixin,
    _PreSilverRecordAdapterMixin,
):
    """Adapt finalized Silver-record flows to the ``PreSilverRecord`` protocol."""

