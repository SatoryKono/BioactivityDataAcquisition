"""UniProt ID Mapping Transformer.

Transforms ID Mapping results into Silver-layer format using
the IDMappingResult domain entity for validation.
"""

from __future__ import annotations

__all__ = ["IDMappingTransformer"]


import dataclasses
from typing import TYPE_CHECKING, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_adapter_mixin import (
    PreSilverAdapterMixin,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.entities.uniprot import IDMappingResult
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class IDMappingTransformer(PreSilverAdapterMixin, BaseTransformer):
    """Transformer for UniProt ID Mapping results.

    Transforms ChEMBL → UniProt mapping results to Silver records.
    Records without a successful mapping have:
    - uniprot_accession: None
    - mapping_status: 'not_found'
    - _dq_warn: True

    Input (Bronze-like): {"target_chembl_id": "CHEMBL204", "uniprot_accession": "P00742"}
    Output (Silver): Full entity with lineage metadata and DQ flags.
    """

    entity_class = IDMappingResult

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "idmapping",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: EntityIdentityGenerator | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize ID Mapping transformer.

        Args:
            provider: Data provider identifier (default: 'uniprot').
            entity_type: Entity type for metrics labels (default: 'idmapping').
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            tracer: Optional tracing collaborator when not using dependencies.
            metrics: Optional metrics collaborator when not using dependencies.
            identity_service: Optional identity collaborator when not using dependencies.
            pii_hasher: Optional PII hasher collaborator when not using dependencies.
            dependencies: Explicit collaborator bundle.
        """
        if dependencies is not None and any(
            value is not None
            for value in (tracer, metrics, identity_service, pii_hasher)
        ):
            dependencies = dataclasses.replace(
                dependencies,
                tracer=tracer if tracer is not None else dependencies.tracer,
                metrics=metrics if metrics is not None else dependencies.metrics,
                identity_service=(
                    identity_service
                    if identity_service is not None
                    else dependencies.identity_service
                ),
                pii_hasher=(
                    pii_hasher if pii_hasher is not None else dependencies.pii_hasher
                ),
            )
            tracer = None
            metrics = None
            identity_service = None
            pii_hasher = None

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
        """Transform ID Mapping result to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Bronze-like record with target_id and entry metadata.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If IDMappingResult entity validation fails.
        """
        target_id, business_data = self._build_mapping_business_data(record)
        return self._transform_identity_business_data(
            context=context,
            source_id=target_id,
            identity_field="target_id",
            index=index,
            business_data=cast(JsonDict, business_data),
        )

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate ID mapping payload for application finalization."""
        del context, index
        target_id, business_data = self._build_mapping_business_data(record)
        return self._stage_identity_business_data(
            source_id=target_id,
            identity_field="target_id",
            business_data=cast(JsonDict, business_data),
        )

    def _build_mapping_business_data(
        self,
        record: BronzeRecord,
    ) -> tuple[str, dict[str, object]]:
        """Build ID mapping business data prior to hash finalization."""
        target_id = str(self._get_required_field(record, "target_id"))
        uniprot_accession = record.get("uniprot_accession")
        all_mappings = record.get("all_mappings")

        if all_mappings:
            mapping_status = "multiple"
        elif uniprot_accession:
            mapping_status = "found"
        else:
            mapping_status = "not_found"

        business_data: dict[str, object] = {
            "target_id": target_id,
            "uniprot_accession": uniprot_accession,
            "mapping_status": mapping_status,
            "uniprot_entry_name": record.get("uniprot_entry_name"),
            "organism_scientific": record.get("organism_scientific"),
            "organism_common": record.get("organism_common"),
            "taxonomy_id": record.get("taxonomy_id"),
            "protein_name": record.get("protein_name"),
            "gene_primary": record.get("gene_primary"),
            "sequence_length": record.get("sequence_length"),
            "sequence_mass": record.get("sequence_mass"),
            "reviewed": record.get("reviewed"),
            "annotation_score": record.get("annotation_score"),
            "all_mappings": all_mappings,
        }
        return target_id, business_data

    def _postprocess_pre_silver_record(
        self,
        silver_record: SilverRecord,
        *,
        business_data: JsonDict,
    ) -> SilverRecord:
        """Mark unmapped ID-mapping results with the staged DQ warning flag."""
        silver_record["_dq_warn"] = business_data.get("mapping_status") == "not_found"
        return cast("SilverRecord", silver_record)
