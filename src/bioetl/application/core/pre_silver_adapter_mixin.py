"""Shared adapters for transformers that participate in staged PreSilver finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict, SilverRecord


class PreSilverAdapterMixin:
    """Adapt finalized Silver-record flows to the ``PreSilverRecord`` protocol."""

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
