"""UniProt ID Mapping Transformer.

Transforms ID Mapping results into Silver-layer format using
the IDMappingResult domain entity for validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities.uniprot import IDMappingResult
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class IDMappingTransformer(BaseTransformer):
    """Transformer for UniProt ID Mapping results.

    Transforms ChEMBL → UniProt mapping results to Silver records.
    Records without a successful mapping have:
    - uniprot_accession: None
    - mapping_status: 'not_found'
    - _dq_warn: True

    Input (Bronze-like): {"target_chembl_id": "CHEMBL204", "uniprot_accession": "P00742"}
    Output (Silver): Full entity with lineage metadata and DQ flags.
    """

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "idmapping",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ):
        """Initialize ID Mapping transformer.

        Args:
            provider: Data provider identifier (default: 'uniprot').
            entity_type: Entity type for metrics labels (default: 'idmapping').
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing sensitive data.
        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
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
            record: Bronze-like record with target_chembl_id and uniprot_accession.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If IDMappingResult entity validation fails.
        """
        # Step 1: Extract required field
        target_chembl_id = self._get_required_field(record, "target_chembl_id")
        uniprot_accession = record.get("uniprot_accession")  # Can be None

        # Step 2: Determine mapping status
        mapping_status = "found" if uniprot_accession else "not_found"

        # Step 3: Build business data dictionary for content hash
        business_data: dict[str, Any] = {
            "target_chembl_id": target_chembl_id,
            "uniprot_accession": uniprot_accession,
            "mapping_status": mapping_status,
        }

        # Step 4: Generate entity_id using IdentityService (RULES.md §2.8)
        entity_id = self.compute_entity_id(
            source_id=target_chembl_id,
            record={"target_chembl_id": target_chembl_id},
        )

        # Step 5: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 6: Create domain entity with lineage metadata
        entity = self._create_entity(
            IDMappingResult,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 7: Convert to SilverRecord with lineage field renaming
        silver_record = self.entity_to_silver_record(entity)

        # Step 8: Set DQ warning flag for not_found mappings
        silver_record["_dq_warn"] = mapping_status != "found"

        return cast("SilverRecord", silver_record)
