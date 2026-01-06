"""Pandera schema for UniProt Protein entity.

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

from datetime import date

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


class ProteinSchema(ETLRecordSchema):
    """UniProt Protein validation schema for Silver layer.

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
        return series.str.match(pattern)

    entry_name: Series[str] = pa.Field(
        nullable=False,
        description="Entry name (e.g., MK01_HUMAN)",
    )

    @pa.check("entry_name", name="entry_name_format")
    def _check_entry_name(cls, series: Series[str]) -> Series[bool]:
        """Validate entry name format."""
        return series.str.match(r"^\w+_\w+$")

    entry_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Entry type (Swiss-Prot reviewed / TrEMBL unreviewed)",
    )

    @pa.check("entry_type", name="entry_type_values")
    def _check_entry_type(cls, series: Series[str]) -> Series[bool]:
        """Validate entry type values."""
        return series.isna() | series.isin(ENTRY_TYPES)

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
        return series.isna() | series.isin(PROTEIN_FLAGS)

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
    taxonomy_id: Series[int] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID"
    )

    @pa.check("taxonomy_id", name="taxonomy_id_positive")
    def _check_taxonomy_id(cls, series: Series[int]) -> Series[bool]:
        """Validate taxonomy ID is positive."""
        return series.isna() | (series >= 1)

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
        return series.isna() | series.isin(PROTEIN_EXISTENCE_LEVELS)

    annotation_score: Series[int] | None = pa.Field(
        nullable=True, description="Annotation quality (1-5 stars)"
    )

    @pa.check("annotation_score", name="annotation_score_range")
    def _check_annotation_score(cls, series: Series[int]) -> Series[bool]:
        """Validate annotation score range."""
        return series.isna() | ((series >= 1) & (series <= 5))

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
        return series.str.match(r"^[ACDEFGHIKLMNPQRSTVWY]+$")

    sequence_length: Series[int] = pa.Field(
        nullable=False, description="Sequence length"
    )

    @pa.check("sequence_length", name="sequence_length_positive")
    def _check_sequence_length(cls, series: Series[int]) -> Series[bool]:
        """Validate sequence length is positive."""
        return series >= 1

    sequence_mass: Series[int] | None = pa.Field(
        nullable=True, description="Molecular mass (Da)"
    )

    @pa.check("sequence_mass", name="sequence_mass_positive")
    def _check_sequence_mass(cls, series: Series[int]) -> Series[bool]:
        """Validate sequence mass is positive."""
        return series.isna() | (series >= 1)

    sequence_checksum: Series[str] | None = pa.Field(
        nullable=True, description="CRC64 checksum"
    )
    sequence_modified: Series[date] | None = pa.Field(
        nullable=True, description="Sequence last modified date"
    )

    # === Entry Metadata ===
    entry_version: Series[int] | None = pa.Field(
        nullable=True, description="Entry version number"
    )

    @pa.check("entry_version", name="entry_version_positive")
    def _check_entry_version(cls, series: Series[int]) -> Series[bool]:
        """Validate entry version is positive."""
        return series.isna() | (series >= 1)

    entry_created: Series[date] | None = pa.Field(
        nullable=True, description="Entry creation date"
    )
    entry_modified: Series[date] | None = pa.Field(
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

    # === Features & Keywords ===
    features: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of sequence features"
    )
    keywords: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of UniProt keywords"
    )

    # === Counts ===
    cross_reference_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of database cross-references"
    )

    @pa.check("cross_reference_count", name="cross_reference_count_non_negative")
    def _check_cross_reference_count(cls, series: Series[int]) -> Series[bool]:
        """Validate cross-reference count is non-negative."""
        return series.isna() | (series >= 0)

    feature_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of sequence features"
    )

    @pa.check("feature_count", name="feature_count_non_negative")
    def _check_feature_count(cls, series: Series[int]) -> Series[bool]:
        """Validate feature count is non-negative."""
        return series.isna() | (series >= 0)

    keyword_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @pa.check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[int]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return series.isna() | (series >= 0)

    publication_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of publications"
    )

    @pa.check("publication_count", name="publication_count_non_negative")
    def _check_publication_count(cls, series: Series[int]) -> Series[bool]:
        """Validate publication count is non-negative."""
        return series.isna() | (series >= 0)

    isoform_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of isoforms"
    )

    @pa.check("isoform_count", name="isoform_count_non_negative")
    def _check_isoform_count(cls, series: Series[int]) -> Series[bool]:
        """Validate isoform count is non-negative."""
        return series.isna() | (series >= 0)

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "ProteinSchema"
        description = "UniProt Protein Silver layer validation"
