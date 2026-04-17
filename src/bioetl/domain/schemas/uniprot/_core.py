# mypy: disable-error-code="untyped-decorator"
"""Core UniProt identifier and metadata fields.

Part of UniprotTargetSchema split to comply with LOC limits.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

__all__ = [
    "ENTRY_TYPES",
    "PROTEIN_EXISTENCE_LEVELS",
    "PROTEIN_FLAGS",
    "UniprotCoreSchema",
]

_SERIES_BOOL = "Series[bool]"


# === Fixed Value Constants ===
PROTEIN_EXISTENCE_LEVELS = [
    "Evidence at protein level",
    "Evidence at transcript level",
    "Inferred from homology",
    "Predicted",
    "Uncertain",
]

ENTRY_TYPES = [
    "UniProtKB reviewed (Swiss-Prot)",
    "UniProtKB unreviewed (TrEMBL)",
]

PROTEIN_FLAGS = ["Fragment", "Precursor", "Fragments"]


class UniprotCoreSchema(ETLRecordSchema):
    """Core identifiers, names, organism and sequence metadata."""

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
        return cast(_SERIES_BOOL, series.str.match(pattern))

    entry_name: Series[str] = pa.Field(
        nullable=False,
        description="Entry name (e.g., MK01_HUMAN)",
    )

    @pa.check("entry_name", name="entry_name_format")
    def _check_entry_name(cls, series: Series[str]) -> Series[bool]:
        """Validate entry name format."""
        return cast(_SERIES_BOOL, series.str.match(r"^\w+_\w+$"))

    entry_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Entry type (Swiss-Prot reviewed / TrEMBL unreviewed)",
    )

    @pa.check("entry_type", name="entry_type_values")
    def _check_entry_type(cls, series: Series[str]) -> Series[bool]:
        """Validate entry type values."""
        return cast(_SERIES_BOOL, series.isna() | series.isin(ENTRY_TYPES))

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
        return cast(_SERIES_BOOL, series.isna() | series.isin(PROTEIN_FLAGS))

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
        return cast(_SERIES_BOOL, series.isna() | (series >= 1))

    lineage: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of taxonomic lineage"
    )

    # === Sequence ===
    sequence: Series[str] = pa.Field(
        nullable=False,
        description="Amino acid sequence",
    )

    @pa.check("sequence", name="sequence_format")
    def _check_sequence(cls, series: Series[str]) -> Series[bool]:
        """Validate amino acid sequence.

        Accepts IUPAC standard + extended amino acid codes:
        - 20 standard: ACDEFGHIKLMNPQRSTVWY
        - U (Selenocysteine), O (Pyrrolysine)
        - B, J, X, Z (ambiguity codes used in UniProt)
        """
        return cast(_SERIES_BOOL, series.str.match(r"^[ACDEFGHIKLMNOPQRSTUVWXYZ]+$"))

    sequence_length: Series[pd.Int64Dtype] = pa.Field(
        nullable=False, description="Sequence length"
    )

    @pa.check("sequence_length", name="sequence_length_positive")
    def _check_sequence_length(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate sequence length is positive."""
        return cast(_SERIES_BOOL, series >= 1)

    sequence_mass: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Molecular mass (Da)"
    )

    @pa.check("sequence_mass", name="sequence_mass_positive")
    def _check_sequence_mass(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate sequence mass is positive."""
        return cast(_SERIES_BOOL, series.isna() | (series >= 1))

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
        return cast(_SERIES_BOOL, series.isna() | (series >= 1))

    entry_created: Series[datetime] | None = pa.Field(
        nullable=True, description="Entry creation date"
    )
    entry_modified: Series[datetime] | None = pa.Field(
        nullable=True, description="Entry last modified date"
    )

    reviewed: Series[bool] = pa.Field(
        nullable=False, description="Swiss-Prot (True) vs TrEMBL (False)"
    )

    protein_existence: Series[str] | None = pa.Field(
        nullable=True,
        description="Evidence level for existence",
    )

    @pa.check("protein_existence", name="protein_existence_values")
    def _check_protein_existence(cls, series: Series[str]) -> Series[bool]:
        """Validate protein existence values."""
        return cast(_SERIES_BOOL, series.isna() | series.isin(PROTEIN_EXISTENCE_LEVELS))

    annotation_score: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Annotation quality (1-5 stars)"
    )

    @pa.check("annotation_score", name="annotation_score_range")
    def _check_annotation_score(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate annotation score range."""
        return cast(_SERIES_BOOL, series.isna() | ((series >= 1) & (series <= 5)))
