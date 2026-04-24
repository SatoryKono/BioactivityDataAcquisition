"""UniProt Target transformer.

Transforms raw UniProt protein records into Silver-layer format using
the UniprotTarget domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.uniprot.transformer_business_data_mixin import (
    UniProtBusinessDataMixin,
)
from bioetl.domain.entities import UniprotTarget
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord, SilverRecord

__all__ = ["UniProtProteinTransformer"]


class UniProtProteinTransformer(BaseTransformer, UniProtBusinessDataMixin):
    """Transformer for UniProt protein records."""

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize UniProt protein transformer."""
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
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)

        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )
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
        return normalizer.project_normalization_findings(
            silver_record,
            context=context,
            index=index,
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
        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=business_data,
            build_silver_record=self._build_pre_silver_json_record,
            apply_structural_policy=self._apply_pre_silver_structural_policy,
            apply_silver_filter=self._apply_pre_silver_filter,
        )

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Build a finalized Silver record from normalized business data."""
        entity = self._create_entity(
            UniprotTarget,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _build_pre_silver_json_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Adapt finalized Silver-record construction to the PreSilverRecord protocol."""
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
        """Adapt structural policy application to the PreSilverRecord protocol."""
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
        """Adapt silver-filter application to the PreSilverRecord protocol."""
        self._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field."""
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)
