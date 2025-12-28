"""GtoPdb Target Transformer.

Transforms raw GtoPdb target records into Silver-layer format using
the GtopdbTarget domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import GtopdbTarget
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class GtopdbTargetTransformer(BaseTransformer):
    """Transformer for GtoPdb target records.

    Uses GtopdbTarget domain entity for validation and lineage tracking.

    GtoPdb API field mapping:
    - targetId -> target_id
    - name -> name
    - abbreviation -> abbreviation
    - systematicName -> systematic_name
    - type -> target_type
    - familyIds -> family_ids (JSON list)
    - species -> species
    - geneSymbol -> gene_symbol
    - geneId -> gene_id
    """

    def __init__(
        self,
        provider: str = "gtopdb",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize GtoPdb target transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
        """
        super().__init__(
            provider,
            entity_type="target",
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw GtoPdb target record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from GtoPdb.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If targetId is missing.
            ValueError: If GtopdbTarget entity validation fails.
        """
        # Step 1: Validate required field
        target_id = self._get_required_field(record, "targetId")

        # Step 2: Build business data dictionary with field mapping
        business_data: dict[str, Any] = {
            "target_id": int(target_id),
            "name": record.get("name"),
            "abbreviation": record.get("abbreviation"),
            "systematic_name": record.get("systematicName"),
            "target_type": record.get("type"),
            # Family hierarchy
            "family_id": self._safe_int(record.get("familyId")),
            "family_name": record.get("familyName"),
            "family_ids": self.serialize_json(record.get("familyIds")),
            # Species information
            "species": record.get("species"),
            "species_id": self._safe_int(record.get("speciesId")),
            # Gene information
            "gene_symbol": record.get("geneSymbol"),
            "gene_id": self._safe_int(record.get("geneId")),
            "ensembl_gene_id": record.get("ensemblGeneId"),
            # UniProt cross-references
            "uniprot_ids": self.serialize_json(record.get("uniprotIds")),
            # Additional identifiers
            "hgnc_id": self._safe_int(record.get("hgncId")),
            "hgnc_symbol": record.get("hgncSymbol"),
            "hgnc_name": record.get("hgncName"),
            # Nomenclature
            "nomenclature_status": record.get("nomenclatureStatus"),
        }

        # Step 3: Generate entity_id
        entity_id = generate_entity_id(
            record={"targetId": target_id},
            provider=self.provider,
            id_field="targetId",
        )

        # Step 4: Compute content_hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        entity = self._create_entity(
            GtopdbTarget,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """Safely convert value to int, returning None if invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
