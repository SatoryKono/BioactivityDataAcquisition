# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Shared adapters for transformers that participate in staged PreSilver finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from bioetl.application.core.pre_silver_finalization_flow import (
    _PreSilverFinalizationFlowMixin,
)
from bioetl.application.core.pre_silver_staging_flow import _PreSilverStagingFlowMixin
from bioetl.domain.types import GoldRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import SilverRecord


class _PreSilverRecordAdapterMixin:
    """Build entity-backed records and adapt Silver hooks to JSON payloads."""

    entity_class: ClassVar[type[object]]

    if TYPE_CHECKING:

        def _create_entity[EntityT](
            self,
            entity_class: type[EntityT],
            context: PipelineContext,
            entity_id: str,
            content_hash: str,
            index: int,
            **business_data: object,
        ) -> EntityT: ...

        def entity_to_silver_record(self, entity: object) -> GoldRecord: ...

        def _apply_structural_policy(
            self,
            context: PipelineContext,
            result: SilverRecord | None,
            index: int,
        ) -> SilverRecord | None: ...

        def _apply_silver_filter(
            self,
            context: PipelineContext,
            result: SilverRecord | None,
            index: int,
        ) -> None: ...

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> GoldRecord:
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )
        silver_record = self.entity_to_silver_record(entity)
        return self._postprocess_pre_silver_record(
            silver_record,
            business_data=business_data,
        )

    def _postprocess_pre_silver_record(
        self,
        silver_record: GoldRecord,
        *,
        business_data: JsonDict,
    ) -> GoldRecord:
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
        return self._build_pre_silver_record(
            context,
            entity_id,
            content_hash,
            index,
            business_data,
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
                cast("SilverRecord", record),  # pyright: ignore[reportInvalidCast]
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
            cast("SilverRecord", record),  # pyright: ignore[reportInvalidCast]
            index,
        )


class PreSilverAdapterMixin(  # pyright: ignore[reportIncompatibleMethodOverride]
    _PreSilverFinalizationFlowMixin,
    _PreSilverStagingFlowMixin,
    _PreSilverRecordAdapterMixin,
):
    """Adapt finalized Silver-record flows to the ``PreSilverRecord`` protocol."""
