"""PreSilver finalization flow mixin."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.pre_silver_identity import PreSilverIdentityHost
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import ContentHash, GoldRecord, SilverRecord

class _PreSilverFinalizationFlowMixin:
    """Finalize staged business payloads into Silver-compatible records."""

    provider: str = ""
    entity_type: str = ""

    if TYPE_CHECKING:

        def compute_content_hash(
            self,
            business_data: JsonDict,
            *,
            exclude_none: bool = True,
        ) -> ContentHash: ...

        def _build_pre_silver_record(
            self,
            context: PipelineContext,
            entity_id: str,
            content_hash: str,
            record_index: int,
            business_data: JsonDict,
        ) -> GoldRecord: ...

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
            silver_record,
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
        identity_host = cast(PreSilverIdentityHost, self)
        entity_id = identity_host.compute_entity_id(source_id, identity_record)
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
            cast(
                object,
                self._finalize_prepared_business_data(
                    context=context,
                    source_id=source_id,
                    identity_record=identity_record,
                    index=index,
                    business_data=business_data,
                ),
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
            silver_record,
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
            cast(
                object,
                self._finalize_normalized_business_data(
                    context=context,
                    index=index,
                    business_data=business_data,
                    resolve_entity_id=resolve_entity_id,
                ),
            ),
        )

__all__ = ["_PreSilverFinalizationFlowMixin"]
