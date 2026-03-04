"""UniProt Target Transformer.

Transforms raw UniProt protein records into Silver-layer format using
the UniprotTarget domain entity for validation and invariant checking.

Delegates data extraction to specialized extractors for maintainability.

.. versionchanged:: 2.0.0
    Uses UniprotTarget (canonical) instead of Protein (deprecated).
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
    TaxonomyExtractor,
)
from bioetl.domain.entities import UniprotTarget
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldRecord

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


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records.

    Uses UniprotTarget domain entity (canonical name) for validation
    and lineage tracking. Records without required fields (accession,
    entry_name) are skipped. protein_name is optional and may be None.

    Delegates extraction logic to specialized extractors:
    - CommentExtractor: functional annotations
    - CrossRefExtractor: GO terms, database references
    - FeatureExtractor: sequence features and keywords
    - GeneExtractor: gene names and synonyms
    - ExtractorUtils: protein names and utilities
    """

    # Pre-defined paths for optimized extraction
    _PROTEIN_DESC_FLAG_PATH = ("proteinDescription", "flag")
    _ORGANISM_SCIENTIFIC_PATH = ("organism", "scientificName")
    _ORGANISM_COMMON_PATH = ("organism", "commonName")
    _ORGANISM_TAXON_ID_PATH = ("organism", "taxonId")
    _ORGANISM_LINEAGE_PATH = ("organism", "lineage")
    _SEQUENCE_VALUE_PATH = ("sequence", "value")
    _SEQUENCE_LENGTH_PATH = ("sequence", "length")
    _SEQUENCE_MOL_WEIGHT_PATH = ("sequence", "molWeight")
    _SEQUENCE_CRC64_PATH = ("sequence", "crc64")
    _SEQUENCE_MODIFIED_PATH = ("sequence", "modified")
    _PROTEIN_NAME_PATH = (
        "proteinDescription",
        "recommendedName",
        "fullName",
        "value",
    )
    # Entry audit paths
    _ENTRY_AUDIT_CREATED_PATH = ("entryAudit", "firstPublicDate")
    _ENTRY_AUDIT_MODIFIED_PATH = ("entryAudit", "lastAnnotationUpdateDate")
    _ENTRY_AUDIT_VERSION_PATH = ("entryAudit", "entryVersion")

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: Any = None,  # Any: contract policy type varies by pipeline
    ):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'protein'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            silver_filters: Optional filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names and other PII.
            data_normalizer: Data normalization service for text normalization.
            contract_policy: Optional pipeline contract policy.
        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
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

        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        entity = self._create_entity(
            UniprotTarget,
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
    ) -> GoldRecord:
        """Build the business data dictionary from record."""
        data: GoldRecord = {"accession": accession, "entry_name": entry_name}

        self._add_core_identifiers(record, data)
        self._add_protein_names(record, data)
        self._add_gene_data(record, data)
        self._add_organism_data(record, data)
        self._add_taxonomy_components(record, data)
        self._add_evidence_data(record, data)
        self._add_sequence_data(record, data)
        self._add_audit_data(record, data)
        self._add_functional_annotations(record, data)
        self._add_cross_references(record, data)
        self._add_go_components(record, data)
        self._add_features_and_keywords(record, data)
        self._add_ptm_features(record, data)
        self._add_isoform_details(record, data)
        self._add_reaction_data(record, data)
        self._add_counts(record, data)

        # Legacy compatibility
        data["organism_id"] = data.get("taxonomy_id")

        return data

    def _add_core_identifiers(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add core identifier fields."""
        data["entry_type"] = record.get("entryType")
        data["secondary_accessions"] = ExtractorUtils.serialize_list(
            record.get("secondaryAccessions")
        )

    def _add_protein_names(self, record: BronzeRecord, data: GoldRecord) -> None:
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
        data["flag"] = self._extract_by_path(record, self._PROTEIN_DESC_FLAG_PATH)

    def _add_gene_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add gene-related fields."""
        genes = record.get("genes")
        data["gene_names"] = self.serialize_json_list(
            GeneExtractor.extract_gene_names(genes)
        )
        data["gene_primary"] = GeneExtractor.extract_primary_gene(genes)
        data["gene_synonyms"] = GeneExtractor.extract_gene_synonyms(genes)
        data["gene_orf_names"] = GeneExtractor.extract_gene_orf_names(genes)

    def _add_organism_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add organism and taxonomy fields."""
        data["organism_scientific"] = self._extract_by_path(
            record, self._ORGANISM_SCIENTIFIC_PATH
        )
        data["organism_common"] = self._extract_by_path(
            record, self._ORGANISM_COMMON_PATH
        )
        data["taxonomy_id"] = self._extract_by_path(
            record, self._ORGANISM_TAXON_ID_PATH
        )
        data["lineage"] = ExtractorUtils.serialize_list(
            self._extract_by_path(record, self._ORGANISM_LINEAGE_PATH)
        )

    def _add_evidence_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add evidence and quality fields."""
        data["protein_existence"] = ExtractorUtils.extract_protein_existence(
            record.get("proteinExistence")
        )
        data["annotation_score"] = record.get("annotationScore")
        data["reviewed"] = ExtractorUtils.is_reviewed(record.get("entryType"))

    def _add_sequence_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add sequence fields."""
        data["sequence"] = self._extract_by_path(record, self._SEQUENCE_VALUE_PATH)
        data["sequence_length"] = self._extract_by_path(
            record, self._SEQUENCE_LENGTH_PATH
        )
        data["sequence_mass"] = self._extract_by_path(
            record, self._SEQUENCE_MOL_WEIGHT_PATH
        )
        data["sequence_checksum"] = self._extract_by_path(
            record, self._SEQUENCE_CRC64_PATH
        )
        # Sequence modification date
        seq_modified_str = self._extract_by_path(record, self._SEQUENCE_MODIFIED_PATH)
        seq_modified_date = ExtractorUtils.parse_uniprot_date(seq_modified_str)
        data["sequence_modified"] = (
            seq_modified_date.isoformat() if seq_modified_date else None
        )

    def _add_audit_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add entry audit metadata fields.

        Extracts entry creation/modification dates and version from entryAudit object.
        Dates are parsed and stored in ISO 8601 format (YYYY-MM-DD).
        """
        # Entry version (integer)
        data["entry_version"] = self._extract_by_path(
            record, self._ENTRY_AUDIT_VERSION_PATH
        )

        # Entry creation date
        created_str = self._extract_by_path(record, self._ENTRY_AUDIT_CREATED_PATH)
        created_date = ExtractorUtils.parse_uniprot_date(created_str)
        data["entry_created"] = created_date.isoformat() if created_date else None

        # Entry last modification date
        modified_str = self._extract_by_path(record, self._ENTRY_AUDIT_MODIFIED_PATH)
        modified_date = ExtractorUtils.parse_uniprot_date(modified_str)
        data["entry_modified"] = modified_date.isoformat() if modified_date else None

    def _add_functional_annotations(
        self, record: BronzeRecord, data: GoldRecord
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

        # Biochemical properties
        data["cofactors"] = CommentExtractor.extract_cofactors(comments)
        data["biophysicochemical_properties"] = (
            CommentExtractor.extract_biophysicochemical_properties(comments)
        )
        data["induction"] = CommentExtractor.extract_induction(comments)

    def _add_cross_references(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add cross-reference fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        data["go_terms"] = CrossRefExtractor.extract_go_terms(xrefs)
        data["drugbank_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "DrugBank")
        data["chembl_ids"] = CrossRefExtractor.extract_xref_ids(xrefs, "ChEMBL")
        data["guidetopharmacology_ids"] = CrossRefExtractor.extract_xref_ids(
            xrefs, "GuidetoPHARMACOLOGY"
        )
        data["pdb_xrefs"] = CrossRefExtractor.extract_pdb_xrefs(xrefs)
        # Extended cross-references for drug discovery
        data["interpro_xrefs"] = CrossRefExtractor.extract_interpro_xrefs(xrefs)
        data["pfam_xrefs"] = CrossRefExtractor.extract_pfam_xrefs(xrefs)
        data["reactome_xrefs"] = CrossRefExtractor.extract_reactome_xrefs(xrefs)

    def _add_features_and_keywords(
        self, record: BronzeRecord, data: GoldRecord
    ) -> None:
        """Add feature and keyword fields."""
        features = record.get("features")
        # All features combined (forensic)
        data["features_json"] = FeatureExtractor.extract_features(features)
        # Specific feature types for analysis
        data["domains"] = FeatureExtractor.extract_domains(features)
        data["binding_sites"] = FeatureExtractor.extract_binding_sites(features)
        data["active_sites"] = FeatureExtractor.extract_active_sites(features)
        # Keywords
        data["keywords"] = FeatureExtractor.extract_keywords(record.get("keywords"))

    def _add_counts(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add count fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        comments = record.get("comments")
        data["cross_reference_count"] = ExtractorUtils.count_list(xrefs)
        data["feature_count"] = ExtractorUtils.count_list(record.get("features"))
        data["keyword_count"] = ExtractorUtils.count_list(record.get("keywords"))
        data["isoform_count"] = CommentExtractor.count_isoforms(comments)

    def _add_taxonomy_components(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add parsed taxonomy lineage components."""
        lineage = self._extract_by_path(record, self._ORGANISM_LINEAGE_PATH)
        taxonomy = TaxonomyExtractor.extract_all(lineage)
        data["superkingdom"] = taxonomy["superkingdom"]
        data["phylum"] = taxonomy["phylum"]
        data["genus"] = taxonomy["genus"]

    def _add_go_components(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add GO terms separated by aspect."""
        xrefs = record.get("uniProtKBCrossReferences")
        data["molecular_function"] = CrossRefExtractor.extract_molecular_function(xrefs)
        data["cellular_component"] = CrossRefExtractor.extract_cellular_component(xrefs)

    def _add_ptm_features(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add PTM and structural features."""
        features = record.get("features")
        data["topology"] = FeatureExtractor.extract_topology(features)
        data["transmembrane"] = FeatureExtractor.extract_transmembrane(features)
        data["intramembrane"] = FeatureExtractor.extract_intramembrane(features)
        data["signal_peptide"] = FeatureExtractor.extract_signal_peptide(features)
        data["propeptide"] = FeatureExtractor.extract_propeptide(features)
        data["glycosylation"] = FeatureExtractor.extract_glycosylation(features)
        data["lipidation"] = FeatureExtractor.extract_lipidation(features)
        data["disulfide_bond"] = FeatureExtractor.extract_disulfide_bonds(features)
        data["modified_residue"] = FeatureExtractor.extract_modified_residues(features)
        data["phosphorylation"] = FeatureExtractor.extract_phosphorylation(features)
        data["acetylation"] = FeatureExtractor.extract_acetylation(features)
        data["ubiquitination"] = FeatureExtractor.extract_ubiquitination(features)

    def _add_isoform_details(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add detailed isoform information."""
        comments = record.get("comments")
        isoform_data = CommentExtractor.extract_isoform_details(comments)
        data["isoform_names"] = isoform_data["isoform_names"]
        data["isoform_ids"] = isoform_data["isoform_ids"]
        data["isoform_synonyms"] = isoform_data["isoform_synonyms"]

    def _add_reaction_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add reaction information from catalytic activity."""
        comments = record.get("comments")
        data["reactions"] = CommentExtractor.extract_reactions(comments)
        data["reaction_ec_numbers"] = CommentExtractor.extract_reaction_ec_numbers(
            comments
        )

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field)."""
        protein_name = self._extract_by_path(
            record,
            self._PROTEIN_NAME_PATH,
        )
        return str(protein_name) if protein_name else None
