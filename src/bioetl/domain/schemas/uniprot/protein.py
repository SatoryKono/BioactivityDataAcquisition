"""Pandera schema for UniProt Target entity.

Aligned with RULES.md v5.0 and UniProt REST API.
Source: https://rest.uniprot.org/uniprotkb/

Extended schema includes:
- Core identifiers and metadata
- Organism & taxonomy information
- Protein names and EC numbers
- Functional annotations (comments)
- Cross-references (GO, DrugBank, ChEMBL, GtoPdb)
- Sequence features and keywords
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
PROTEIN_EXISTENCE_LEVELS = [
    "Evidence at protein level",
    "Evidence at transcript level",
    "Inferred from homology",
    "Predicted",
    "Uncertain",
]

# Entry types from UniProt API
ENTRY_TYPES = [
    "UniProtKB reviewed (Swiss-Prot)",
    "UniProtKB unreviewed (TrEMBL)",
]

# Protein sequence completeness flags
PROTEIN_FLAGS = ["Fragment", "Precursor", "Fragments"]


class UniprotTargetSchema(ETLRecordSchema):
    """UniProt Target validation schema for Silver layer.

    Represents a UniProtKB protein entry (Swiss-Prot or TrEMBL).
    """

    # === Primary Key & Core Identifiers ===
    accession: Series[str] = pa.Field(
        nullable=False,
        description="UniProt primary accession (PK)",
    )

    @pa.check("accession", name="accession_format")
    def _check_accession(cls, series: Series[str]) -> Series[bool]:
        """Validate UniProt accession format."""
        pattern = (
            r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
        )
        return cast("Series[bool]", series.str.match(pattern))

    entry_name: Series[str] = pa.Field(
        nullable=False,
        description="Entry name (e.g., MK01_HUMAN)",
    )

    @pa.check("entry_name", name="entry_name_format")
    def _check_entry_name(cls, series: Series[str]) -> Series[bool]:
        """Validate entry name format."""
        return cast("Series[bool]", series.str.match(r"^\w+_\w+$"))

    entry_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Entry type (Swiss-Prot reviewed / TrEMBL unreviewed)",
    )

    @pa.check("entry_type", name="entry_type_values")
    def _check_entry_type(cls, series: Series[str]) -> Series[bool]:
        """Validate entry type values."""
        return cast("Series[bool]", series.isna() | series.isin(ENTRY_TYPES))

    secondary_accessions: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of secondary accessions"
    )

    # === Protein Names ===
    protein_name: Series[str] | None = pa.Field(
        nullable=True, description="Recommended protein name"
    )
    protein_short_names: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of short names"
    )
    protein_alternative_names: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of alternative protein names"
    )
    protein_ec_numbers: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of EC numbers"
    )
    flag: Series[str] | None = pa.Field(
        nullable=True,
        description="Protein sequence completeness flag (Fragment/Precursor)",
    )

    @pa.check("flag", name="flag_values")
    def _check_flag(cls, series: Series[str]) -> Series[bool]:
        """Validate flag values."""
        return cast("Series[bool]", series.isna() | series.isin(PROTEIN_FLAGS))

    # === Gene Names ===
    gene_primary: Series[str] | None = pa.Field(
        nullable=True, description="Primary gene name"
    )
    gene_synonyms: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of gene synonyms"
    )
    gene_orf_names: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of ORF names"
    )

    # === Organism ===
    organism_scientific: Series[str] | None = pa.Field(
        nullable=True, description="Scientific organism name"
    )
    organism_common: Series[str] | None = pa.Field(
        nullable=True, description="Common organism name"
    )
    taxonomy_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID"
    )

    @pa.check("taxonomy_id", name="taxonomy_id_positive")
    def _check_taxonomy_id(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate taxonomy ID is positive."""
        return cast("Series[bool]", series.isna() | (series >= 1))

    lineage: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of taxonomic lineage"
    )

    # === Evidence & Quality ===
    protein_existence: Series[str] | None = pa.Field(
        nullable=True,
        description="Evidence level for existence",
    )

    @pa.check("protein_existence", name="protein_existence_values")
    def _check_protein_existence(cls, series: Series[str]) -> Series[bool]:
        """Validate protein existence values."""
        return cast(
            "Series[bool]", series.isna() | series.isin(PROTEIN_EXISTENCE_LEVELS)
        )

    annotation_score: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Annotation quality (1-5 stars)"
    )

    @pa.check("annotation_score", name="annotation_score_range")
    def _check_annotation_score(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate annotation score range."""
        return cast("Series[bool]", series.isna() | ((series >= 1) & (series <= 5)))

    reviewed: Series[bool] = pa.Field(
        nullable=False, description="Swiss-Prot (True) vs TrEMBL (False)"
    )

    # === Sequence ===
    sequence: Series[str] = pa.Field(
        nullable=False,
        description="Amino acid sequence",
    )

    @pa.check("sequence", name="sequence_format")
    def _check_sequence(cls, series: Series[str]) -> Series[bool]:
        """Validate amino acid sequence."""
        return cast("Series[bool]", series.str.match(r"^[ACDEFGHIKLMNPQRSTVWY]+$"))

    sequence_length: Series[pd.Int64Dtype] = pa.Field(
        nullable=False, description="Sequence length"
    )

    @pa.check("sequence_length", name="sequence_length_positive")
    def _check_sequence_length(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate sequence length is positive."""
        return cast("Series[bool]", series >= 1)

    sequence_mass: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Molecular mass (Da)"
    )

    @pa.check("sequence_mass", name="sequence_mass_positive")
    def _check_sequence_mass(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate sequence mass is positive."""
        return cast("Series[bool]", series.isna() | (series >= 1))

    sequence_checksum: Series[str] | None = pa.Field(
        nullable=True, description="CRC64 checksum"
    )
    sequence_modified: Series[datetime] | None = pa.Field(
        nullable=True, description="Sequence last modified date"
    )

    # === Entry Metadata ===
    entry_version: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Entry version number"
    )

    @pa.check("entry_version", name="entry_version_positive")
    def _check_entry_version(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate entry version is positive."""
        return cast("Series[bool]", series.isna() | (series >= 1))

    entry_created: Series[datetime] | None = pa.Field(
        nullable=True, description="Entry creation date"
    )
    entry_modified: Series[datetime] | None = pa.Field(
        nullable=True, description="Entry last modified date"
    )

    # === Functional Annotation ===
    function_comment: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of function descriptions"
    )
    catalytic_activity: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of catalytic reactions"
    )
    activity_regulation: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of activity regulation info"
    )
    subunit: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of subunit structure info"
    )
    pathway: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of pathways"
    )
    subcellular_location: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of subcellular locations"
    )
    tissue_specificity: Series[str] | None = pa.Field(
        nullable=True, description="Tissue expression pattern"
    )
    alternative_products: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of alternative splicing/isoforms"
    )
    disease_involvement: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of disease associations"
    )
    pharmaceutical_use: Series[str] | None = pa.Field(
        nullable=True, description="Pharmaceutical applications"
    )
    similarity_comment: Series[str] | None = pa.Field(
        nullable=True, description="Family and domain information"
    )
    caution: Series[str] | None = pa.Field(
        nullable=True, description="Warnings about this entry"
    )

    # === Biochemical Properties ===
    cofactors: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of cofactors with name and ChEBI ID",
    )
    biophysicochemical_properties: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON object with pH/temp optima, kinetics, redox potential",
    )
    induction: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of gene expression induction conditions",
    )

    # === Cross-References (Extracted) ===
    go_terms: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of GO terms with evidence codes"
    )
    drugbank_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of DrugBank identifiers"
    )
    chembl_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of ChEMBL target identifiers"
    )
    guidetopharmacology_ids: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of Guide to Pharmacology identifiers"
    )
    pdb_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of PDB cross-references with structure details",
    )
    interpro_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of InterPro domain entries with id and name",
    )
    pfam_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of Pfam family entries with id, name, and match_status",
    )
    reactome_xrefs: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of Reactome pathway entries with id and pathway_name",
    )

    # === Features & Keywords ===
    features_json: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of all sequence features"
    )
    domains: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of protein domain features"
    )
    binding_sites: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of binding site features"
    )
    active_sites: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of active site features"
    )
    keywords: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of UniProt keywords"
    )

    # === Taxonomy Components ===
    superkingdom: Series[str] | None = pa.Field(
        nullable=True,
        description="Superkingdom/Domain (Bacteria, Archaea, Eukaryota, Viruses)",
    )
    phylum: Series[str] | None = pa.Field(
        nullable=True,
        description="Phylum from taxonomic lineage",
    )
    genus: Series[str] | None = pa.Field(
        nullable=True,
        description="Genus from taxonomic lineage",
    )

    # === GO Components ===
    molecular_function: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of GO molecular function terms (aspect F)",
    )
    cellular_component: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of GO cellular component terms (aspect C)",
    )

    # === Structural Features ===
    topology: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of topological domain features (TOPO_DOM)",
    )
    transmembrane: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of transmembrane regions (TRANSMEM)",
    )
    intramembrane: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of intramembrane regions (INTRAMEM)",
    )
    signal_peptide: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of signal peptide features (SIGNAL)",
    )
    propeptide: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of propeptide features (PROPEP)",
    )

    # === PTM Features ===
    glycosylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of glycosylation sites (CARBOHYD)",
    )
    lipidation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of lipidation sites (LIPID)",
    )
    disulfide_bond: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of disulfide bonds (DISULFID)",
    )
    modified_residue: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of all modified residues (MOD_RES)",
    )
    phosphorylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of phosphorylation sites",
    )
    acetylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of acetylation sites",
    )
    ubiquitination: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of ubiquitination sites",
    )

    # === Isoform Details ===
    isoform_names: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform names",
    )
    isoform_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform IDs (e.g., P12345-2)",
    )
    isoform_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform synonyms",
    )

    # === Reaction Data ===
    reactions: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of reaction names from catalytic activity",
    )
    reaction_ec_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of EC numbers from catalytic activity reactions",
    )

    # === Counts ===
    cross_reference_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of database cross-references"
    )

    @pa.check("cross_reference_count", name="cross_reference_count_non_negative")
    def _check_cross_reference_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate cross-reference count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of sequence features"
    )

    @pa.check("feature_count", name="feature_count_non_negative")
    def _check_feature_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate feature count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    keyword_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @pa.check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    publication_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of publications"
    )

    @pa.check("publication_count", name="publication_count_non_negative")
    def _check_publication_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate publication count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    isoform_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of isoforms"
    )

    @pa.check("isoform_count", name="isoform_count_non_negative")
    def _check_isoform_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate isoform count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = False
        coerce = True
        name = "UniprotTargetSchema"
        description = "UniProt Target Silver layer validation"


__all__ = [
    "UniprotTargetSchema",
]
