"""UniProt Target transformer.

Transforms raw UniProt protein records into Silver-layer format using
the UniprotTarget domain entity for validation and invariant checking.
"""

from __future__ import annotations

__all__ = ["UniProtProteinTransformer"]

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_adapter_mixin import (
    PreSilverAdapterMixin,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.uniprot.transformer_business_data_mixin import (
    UniProtBusinessDataMixin,
)
from bioetl.domain.entities import UniprotTarget
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(
    PreSilverAdapterMixin, BaseTransformer, UniProtBusinessDataMixin
):
    """Transformer for UniProt protein records."""

    entity_class = UniprotTarget

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: EntityIdentityGenerator | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize UniProt protein transformer with provider defaults."""
        super().__init__(
            provider,
            entity_type=entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format."""
        accession = str(self._get_required_field(record, "primaryAccession"))
        entry_name = self._get_entry_name(record)
        business_data = self._build_business_data(record, accession, entry_name)
        return self._transform_identity_business_data(
            context=context,
            source_id=accession,
            identity_field="accession",
            index=index,
            business_data=cast(JsonDict, business_data),
        )

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate UniProt payload for application finalization."""
        accession = str(self._get_required_field(record, "primaryAccession"))
        entry_name = self._get_entry_name(record)
        business_data = self._build_business_data(record, accession, entry_name)
        return self._stage_identity_business_data(
            source_id=accession,
            identity_field="accession",
            business_data=cast(JsonDict, business_data),
        )

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field."""
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)
