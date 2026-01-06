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

import pandera as pa
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
        str_matches=r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$",
        description="UniProt primary accession (PK)",
    )
    entry_name: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^\w+_\w+$",
        description="Entry name (e.g., MK01_HUMAN)",
    )
    entry_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=ENTRY_TYPES,
        description="Entry type (Swiss-Prot reviewed / TrEMBL unreviewed)",
    )
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
        isin=PROTEIN_FLAGS,
        description="Protein sequence completeness flag (Fragment/Precursor)",
    )

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
        nullable=True, ge=1, description="NCBI Taxonomy ID"
    )
    lineage: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of taxonomic lineage"
    )

    # === Evidence & Quality ===
    protein_existence: Series[str] | None = pa.Field(
        nullable=True,
        isin=PROTEIN_EXISTENCE_LEVELS,
        description="Evidence level for existence",
    )
    annotation_score: Series[int] | None = pa.Field(
        nullable=True, ge=1, le=5, description="Annotation quality (1-5 stars)"
    )
    reviewed: Series[bool] = pa.Field(
        nullable=False, description="Swiss-Prot (True) vs TrEMBL (False)"
    )

    # === Sequence ===
    sequence: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[ACDEFGHIKLMNPQRSTVWY]+$",
        description="Amino acid sequence",
    )
    sequence_length: Series[int] = pa.Field(
        nullable=False, ge=1, description="Sequence length"
    )
    sequence_mass: Series[int] | None = pa.Field(
        nullable=True, ge=1, description="Molecular mass (Da)"
    )
    sequence_checksum: Series[str] | None = pa.Field(
        nullable=True, description="CRC64 checksum"
    )
    sequence_modified: Series[date] | None = pa.Field(
        nullable=True, description="Sequence last modified date"
    )

    # === Entry Metadata ===
    entry_version: Series[int] | None = pa.Field(
        nullable=True, ge=1, description="Entry version number"
    )
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
        nullable=True, ge=0, description="Number of database cross-references"
    )
    feature_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of sequence features"
    )
    keyword_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of keywords"
    )
    publication_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of publications"
    )
    isoform_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of isoforms"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "ProteinSchema"
        description = "UniProt Protein Silver layer validation"
