"""Pandera schema for UniProt Protein entity.

Aligned with RULES.md v5.0 and UniProt REST API.
Source: https://rest.uniprot.org/uniprotkb/
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


# === Fixed Value Constants ===
PROTEIN_EXISTENCE_LEVELS = [
    "Evidence at protein level",
    "Evidence at transcript level",
    "Inferred from homology",
    "Predicted",
    "Uncertain"
]


class ProteinSchema(ETLRecordSchema):
    """UniProt Protein validation schema for Silver layer.

    Represents a UniProtKB protein entry (Swiss-Prot or TrEMBL).
    """

    # === Primary Key ===
    accession: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$",
        description="UniProt accession (PK)"
    )
    entry_name: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^\w+_\w+$",
        description="Entry name (e.g., MK01_HUMAN)"
    )

    # === Protein Names ===
    protein_name: Series[str] = pa.Field(
        nullable=False,
        description="Recommended protein name"
    )
    protein_short_names: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of short names"
    )
    protein_ec_numbers: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of EC numbers"
    )

    # === Gene Names ===
    gene_primary: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Primary gene name"
    )
    gene_synonyms: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of gene synonyms"
    )
    gene_orf_names: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of ORF names"
    )

    # === Organism ===
    organism_scientific: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Scientific organism name"
    )
    organism_common: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Common organism name"
    )
    taxonomy_id: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        description="NCBI Taxonomy ID"
    )
    lineage: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of taxonomic lineage"
    )

    # === Evidence & Quality ===
    protein_existence: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=PROTEIN_EXISTENCE_LEVELS,
        description="Evidence level for existence"
    )
    annotation_score: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        le=5,
        description="Annotation quality (1-5 stars)"
    )
    reviewed: Series[bool] = pa.Field(
        nullable=False,
        description="Swiss-Prot (True) vs TrEMBL (False)"
    )

    # === Sequence ===
    sequence: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[ACDEFGHIKLMNPQRSTVWY]+$",
        description="Amino acid sequence"
    )
    sequence_length: Series[int] = pa.Field(
        nullable=False,
        ge=1,
        description="Sequence length"
    )
    sequence_mass: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        description="Molecular mass (Da)"
    )
    sequence_checksum: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="CRC64 checksum"
    )
    sequence_modified: Optional[Series[date]] = pa.Field(
        nullable=True,
        description="Sequence last modified date"
    )

    # === Entry Metadata ===
    entry_version: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        description="Entry version number"
    )
    entry_created: Optional[Series[date]] = pa.Field(
        nullable=True,
        description="Entry creation date"
    )
    entry_modified: Optional[Series[date]] = pa.Field(
        nullable=True,
        description="Entry last modified date"
    )

    # === Functional Annotation ===
    function_comment: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Function description"
    )
    catalytic_activity: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of catalytic reactions"
    )
    pathway: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of pathways"
    )
    subcellular_location: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of subcellular locations"
    )
    tissue_specificity: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Tissue expression pattern"
    )
    disease_involvement: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of disease associations"
    )
    pharmaceutical_use: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Pharmaceutical applications"
    )
    similarity_comment: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Family and domain information"
    )
    caution: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Warnings about this entry"
    )

    # === Counts ===
    cross_reference_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of database cross-references"
    )
    feature_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of sequence features"
    )
    keyword_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of keywords"
    )
    publication_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of publications"
    )
    isoform_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of isoforms"
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
        name = "ProteinSchema"
        description = "UniProt Protein Silver layer validation"
