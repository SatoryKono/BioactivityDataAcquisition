"""PreSilver finalization flow mixin."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import SilverRecord


class _PreSilverFinalizationOwner(Protocol):
    """Transformer surface required by the finalization flow."""

    def compute_content_hash(
        self,
        business_data: JsonDict,
        *,
        exclude_none: bool = True,
    ) -> str: ...

    def compute_entity_id(
        self,
        source_id: str | None,
        record: JsonDict,
    ) -> str: ...

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord: ...


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
        return self._build_record_normalizer().project_normalization_findings(
            silver_record,
            context=context,
            index=index,
        )

    def _finalize_staged_business_data(
        self,
        *,
        context: PipelineContext,
        entity_id: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        owner = cast("_PreSilverFinalizationOwner", self)
        normalized_business_data = self._normalize_business_data(business_data)
        content_hash = owner.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = owner._build_pre_silver_record(
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
        owner = cast("_PreSilverFinalizationOwner", self)
        entity_id = owner.compute_entity_id(
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
        owner = cast("_PreSilverFinalizationOwner", self)
        normalized_business_data = self._normalize_business_data(business_data)
        entity_id = resolve_entity_id(normalized_business_data)
        content_hash = owner.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = owner._build_pre_silver_record(
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


__all__ = ["_PreSilverFinalizationFlowMixin"]
