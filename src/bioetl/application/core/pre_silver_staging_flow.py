"""PreSilver staging flow mixin."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.pre_silver_identity import PreSilverIdentityHost
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class _PreSilverStagingFlowMixin:
    """Stage business payloads behind the ``PreSilverRecord`` protocol."""

    if TYPE_CHECKING:

        def _build_pre_silver_json_record(
            self,
            context: PipelineContext,
            entity_id: str,
            content_hash: str,
            index: int,
            business_data: JsonDict,
        ) -> JsonDict: ...

        def _apply_pre_silver_structural_policy(
            self,
            context: PipelineContext,
            record: JsonDict,
            index: int,
        ) -> JsonDict | None: ...

        def _apply_pre_silver_filter(
            self,
            context: PipelineContext,
            record: JsonDict,
            index: int,
        ) -> None: ...

        def _normalize_business_data(self, business_data: JsonDict) -> JsonDict: ...

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
        identity_host = cast(PreSilverIdentityHost, self)
        entity_id = identity_host.compute_entity_id(
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


__all__ = ["_PreSilverStagingFlowMixin"]
