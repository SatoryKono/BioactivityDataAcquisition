"""Template for a new transformer (legacy file name kept for compatibility).

Location: src/bioetl/application/pipelines/<provider>/<entity>_transformer.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class {{Provider}}{{Entity}}Transformer(BaseTransformer):
    """Transformer for {{provider}}/{{entity}} records."""

    def __init__(
        self,
        provider: str = "{{provider}}",
        entity_type: str = "{{entity}}",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform one Bronze record into a Silver record."""
        {{primary_key}} = self._get_required_field(record, "{{primary_key}}")

        business_data: dict[str, Any] = {
            "{{primary_key}}": str({{primary_key}}),
            # "field_1": record.get("source_field_1"),
        }

        entity_id = self.compute_entity_id(
            source_id=str({{primary_key}}),
            record={"{{primary_key}}": {{primary_key}}},
        )
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        silver_record: dict[str, Any] = {
            **business_data,
            "entity_id": entity_id,
            "content_hash": content_hash,
        }
        return cast("SilverRecord", silver_record)
