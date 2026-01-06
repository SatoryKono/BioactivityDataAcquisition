"""UniProt Protein Transformer.

Transforms raw UniProt protein records into Silver-layer format using
the Protein domain entity for validation and invariant checking.

Delegates data extraction to specialized extractors for maintainability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.application.pipelines.uniprot.extractors import (
    CommentExtractor,
    CrossRefExtractor,
    ExtractorUtils,
    FeatureExtractor,
    GeneExtractor,
)
from bioetl.domain.entities import Protein
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records.

    Uses Protein domain entity for validation and lineage tracking.
    Records without required fields (accession, entry_name) are skipped.
    protein_name is optional and may be None.

    Delegates extraction logic to specialized extractors:
    - CommentExtractor: functional annotations
    - CrossRefExtractor: GO terms, database references
    - FeatureExtractor: sequence features and keywords
    - GeneExtractor: gene names and synonyms
    - ExtractorUtils: protein names and utilities
    """

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'protein'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names and other PII.
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
        """Transform raw UniProt record to Silver format."""
        accession = self._get_required_field(record, "primaryAccession")
        entry_name = self._get_entry_name(record)

        business_data = self._build_business_data(record, accession, entry_name)

        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        entity = self._create_entity(
            Protein,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field."""
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)

    def _build_business_data(
        self, record: BronzeRecord, accession: str, entry_name: str
    ) -> dict[str, Any]:
        """Build the business data dictionary from record."""
        data: dict[str, Any] = {"accession": accession, "entry_name": entry_name}

        self._add_core_identifiers(record, data)
        self._add_protein_names(record, data)
        self._add_gene_data(record, data)
        self._add_organism_data(record, data)
        self._add_evidence_data(record, data)
        self._add_sequence_data(record, data)
        self._add_functional_annotations(record, data)
        self._add_cross_references(record, data)
        self._add_features_and_keywords(record, data)
        self._add_counts(record, data)

        # Legacy compatibility
        data["organism_id"] = data.get("taxonomy_id")

        return data

    def _add_core_identifiers(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add core identifier fields."""
        data["entry_type"] = record.get("entryType")
        data["secondary_accessions"] = ExtractorUtils.serialize_list(
            record.get("secondaryAccessions")
        )

    def _add_protein_names(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add protein name fields."""
        protein_desc = record.get("proteinDescription", {})
        recommended_name = (
            protein_desc.get("recommendedName")
            if isinstance(protein_desc, dict)
            else None
        )

        data["protein_name"] = self._extract_protein_name(record)
        data["protein_short_names"] = ExtractorUtils.extract_short_names(
            recommended_name
        )
        data["protein_alternative_names"] = ExtractorUtils.extract_alternative_names(
            protein_desc
        )
        data["protein_ec_numbers"] = ExtractorUtils.extract_ec_numbers(recommended_name)
        data["flag"] = self._extract_nested(record, "proteinDescription.flag")

    def _add_gene_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add gene-related fields."""
        genes = record.get("genes")
        data["gene_names"] = GeneExtractor.extract_gene_names(genes)
        data["gene_primary"] = GeneExtractor.extract_primary_gene(genes)
        data["gene_synonyms"] = GeneExtractor.extract_gene_synonyms(genes)
        data["gene_orf_names"] = GeneExtractor.extract_gene_orf_names(genes)

    def _add_organism_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add organism and taxonomy fields."""
        data["organism_scientific"] = self._extract_nested(
            record, "organism.scientificName"
        )
        data["organism_common"] = self._extract_nested(record, "organism.commonName")
        data["taxonomy_id"] = self._extract_nested(record, "organism.taxonId")
        data["lineage"] = ExtractorUtils.serialize_list(
            self._extract_nested(record, "organism.lineage")
        )

    def _add_evidence_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add evidence and quality fields."""
        data["protein_existence"] = ExtractorUtils.extract_protein_existence(
            record.get("proteinExistence")
        )
        data["annotation_score"] = record.get("annotationScore")
        data["reviewed"] = ExtractorUtils.is_reviewed(record.get("entryType"))

    def _add_sequence_data(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add sequence fields."""
        data["sequence"] = self._extract_nested(record, "sequence.value")
        data["sequence_length"] = self._extract_nested(record, "sequence.length")
        data["sequence_mass"] = self._extract_nested(record, "sequence.molWeight")
        data["sequence_checksum"] = self._extract_nested(record, "sequence.crc64")

    def _add_functional_annotations(
        self, record: BronzeRecord, data: dict[str, Any]
    ) -> None:
        """Add functional annotation fields."""
        comments = record.get("comments")
        data["function_comment"] = CommentExtractor.extract_by_type(
            comments, "FUNCTION"
        )
        data["catalytic_activity"] = CommentExtractor.extract_catalytic_activity(
            comments
        )
        data["activity_regulation"] = CommentExtractor.extract_by_type(
            comments, "ACTIVITY REGULATION"
        )
        data["subunit"] = CommentExtractor.extract_by_type(comments, "SUBUNIT")
        data["pathway"] = CommentExtractor.extract_by_type(comments, "PATHWAY")
        data["subcellular_location"] = CommentExtractor.extract_subcellular_locations(
            comments
        )
        data["tissue_specificity"] = CommentExtractor.extract_by_type(
            comments, "TISSUE SPECIFICITY"
        )
        data["alternative_products"] = CommentExtractor.extract_alternative_products(
            comments
        )
        data["disease_involvement"] = CommentExtractor.extract_by_type(
            comments, "DISEASE"
        )
        data["similarity_comment"] = CommentExtractor.extract_by_type(
            comments, "SIMILARITY"
        )
        data["caution"] = CommentExtractor.extract_by_type(comments, "CAUTION")

    def _add_cross_references(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add cross-reference fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        data["go_terms"] = CrossRefExtractor.extract_go_terms(xrefs)
        data["drugbank_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "DrugBank")
        data["chembl_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "ChEMBL")
        data["guidetopharmacology_ids"] = CrossRefExtractor.extract_xref_ids(
            xrefs, "GuidetoPHARMACOLOGY"
        )

    def _add_features_and_keywords(
        self, record: BronzeRecord, data: dict[str, Any]
    ) -> None:
        """Add feature and keyword fields."""
        data["features"] = FeatureExtractor.extract_features(record.get("features"))
        data["keywords"] = FeatureExtractor.extract_keywords(record.get("keywords"))

    def _add_counts(self, record: BronzeRecord, data: dict[str, Any]) -> None:
        """Add count fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        comments = record.get("comments")
        data["cross_reference_count"] = ExtractorUtils.count_list(xrefs)
        data["feature_count"] = ExtractorUtils.count_list(record.get("features"))
        data["keyword_count"] = ExtractorUtils.count_list(record.get("keywords"))
        data["isoform_count"] = CommentExtractor.count_isoforms(comments)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field)."""
        protein_name = self._extract_nested(
            record,
            "proteinDescription.recommendedName.fullName.value",
        )
        return str(protein_name) if protein_name else None
