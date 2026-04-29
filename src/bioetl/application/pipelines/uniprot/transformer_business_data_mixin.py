"""Business-data assembly mixin for UniProt protein transformer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.pipelines.uniprot.extractors import (
    CommentExtractor,
    CrossRefExtractor,
    ExtractorHelper,
    FeatureExtractor,
    GeneExtractor,
    TaxonomyExtractor,
)
from bioetl.domain.types import GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class UniProtBusinessDataMixin:
    """Builds UniProt business payload from a Bronze record."""

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
    _ENTRY_AUDIT_CREATED_PATH = ("entryAudit", "firstPublicDate")
    _ENTRY_AUDIT_MODIFIED_PATH = ("entryAudit", "lastAnnotationUpdateDate")
    _ENTRY_AUDIT_VERSION_PATH = ("entryAudit", "entryVersion")

    def _extract_by_path(
        self,
        data: BronzeRecord,
        path: Sequence[str],
        default: object | None = None,
    ) -> object | None:
        raise NotImplementedError

    def serialize_json_list(self, values: Sequence[object] | None) -> str | None:
        """Serialize a list of values to a JSON string, or None if empty."""
        raise NotImplementedError

    def _build_business_data(
        self, record: BronzeRecord, accession: str, entry_name: str
    ) -> GoldRecord:
        """Build business payload from UniProt source record."""
        data: GoldRecord = {"accession": accession, "entry_name": entry_name}
        comment_data = CommentExtractor.extract_all_comments(record.get("comments"))

        self._add_core_identifiers(record, data)
        self._add_protein_names(record, data)
        self._add_gene_data(record, data)
        self._add_organism_data(record, data)
        self._add_taxonomy_components(record, data)
        self._add_evidence_data(record, data)
        self._add_sequence_data(record, data)
        self._add_audit_data(record, data)
        self._add_comment_annotations(data, comment_data)
        self._add_cross_references(record, data)
        self._add_go_components(record, data)
        self._add_features_and_keywords(record, data)
        self._add_ptm_features(record, data)

        raw_isoform_count = comment_data.get("isoform_count")
        isoform_count = (
            raw_isoform_count if isinstance(raw_isoform_count, int) else None
        )
        self._add_counts(record, data, isoform_count=isoform_count)

        return data

    def _add_core_identifiers(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add core identifier fields."""
        data["entry_type"] = record.get("entryType")
        data["secondary_accessions"] = ExtractorHelper.serialize_list(
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
        data["protein_short_names"] = ExtractorHelper.extract_short_names(
            recommended_name
        )
        data["protein_alternative_names"] = ExtractorHelper.extract_alternative_names(
            protein_desc
        )
        data["protein_ec_numbers"] = ExtractorHelper.extract_ec_numbers(
            recommended_name
        )
        data["flag"] = self._extract_by_path(record, self._PROTEIN_DESC_FLAG_PATH)

    def _add_gene_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add gene-related fields."""
        genes = record.get("genes")
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
        data["lineage"] = ExtractorHelper.serialize_list(
            self._extract_by_path(record, self._ORGANISM_LINEAGE_PATH)
        )

    def _add_evidence_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add evidence and quality fields."""
        data["protein_existence"] = ExtractorHelper.extract_protein_existence(
            record.get("proteinExistence")
        )
        data["annotation_score"] = record.get("annotationScore")
        data["reviewed"] = ExtractorHelper.is_reviewed(record.get("entryType"))

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
        seq_modified_str = self._extract_by_path(record, self._SEQUENCE_MODIFIED_PATH)
        seq_modified_date = ExtractorHelper.parse_uniprot_date(seq_modified_str)
        data["sequence_modified"] = (
            seq_modified_date.isoformat() if seq_modified_date else None
        )

    def _add_audit_data(self, record: BronzeRecord, data: GoldRecord) -> None:
        """Add entry audit metadata fields."""
        data["entry_version"] = self._extract_by_path(
            record, self._ENTRY_AUDIT_VERSION_PATH
        )

        created_str = self._extract_by_path(record, self._ENTRY_AUDIT_CREATED_PATH)
        created_date = ExtractorHelper.parse_uniprot_date(created_str)
        data["entry_created"] = created_date.isoformat() if created_date else None

        modified_str = self._extract_by_path(record, self._ENTRY_AUDIT_MODIFIED_PATH)
        modified_date = ExtractorHelper.parse_uniprot_date(modified_str)
        data["entry_modified"] = modified_date.isoformat() if modified_date else None

    def _add_comment_annotations(
        self,
        data: GoldRecord,
        comment_data: dict[str, str | int | None],
    ) -> None:
        """Add comment-derived fields from precomputed extractor output."""
        comment_fields: tuple[str, ...] = (
            "function_comment",
            "catalytic_activity",
            "activity_regulation",
            "subunit",
            "pathway",
            "subcellular_location",
            "tissue_specificity",
            "alternative_products",
            "disease_involvement",
            "similarity_comment",
            "caution",
            "cofactors",
            "biophysicochemical_properties",
            "induction",
            "isoform_names",
            "isoform_ids",
            "isoform_synonyms",
            "reactions",
            "reaction_ec_numbers",
        )
        for field_name in comment_fields:
            data[field_name] = comment_data.get(field_name)

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
        data["interpro_xrefs"] = CrossRefExtractor.extract_interpro_xrefs(xrefs)
        data["pfam_xrefs"] = CrossRefExtractor.extract_pfam_xrefs(xrefs)
        data["reactome_xrefs"] = CrossRefExtractor.extract_reactome_xrefs(xrefs)

    def _add_features_and_keywords(
        self, record: BronzeRecord, data: GoldRecord
    ) -> None:
        """Add feature and keyword fields."""
        features = record.get("features")
        data["features_json"] = FeatureExtractor.extract_features(features)
        data["domains"] = FeatureExtractor.extract_domains(features)
        data["binding_sites"] = FeatureExtractor.extract_binding_sites(features)
        data["active_sites"] = FeatureExtractor.extract_active_sites(features)
        data["keywords"] = FeatureExtractor.extract_keywords(record.get("keywords"))

    def _add_counts(
        self,
        record: BronzeRecord,
        data: GoldRecord,
        *,
        isoform_count: int | None = None,
    ) -> None:
        """Add count fields."""
        xrefs = record.get("uniProtKBCrossReferences")
        data["cross_reference_count"] = ExtractorHelper.count_list(xrefs)
        data["feature_count"] = ExtractorHelper.count_list(record.get("features"))
        data["keyword_count"] = ExtractorHelper.count_list(record.get("keywords"))
        data["isoform_count"] = isoform_count

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

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field)."""
        protein_name = self._extract_by_path(record, self._PROTEIN_NAME_PATH)
        return str(protein_name) if protein_name else None


__all__ = ["UniProtBusinessDataMixin"]
