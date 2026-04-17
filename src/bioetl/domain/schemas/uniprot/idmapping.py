# mypy: disable-error-code="untyped-decorator"
"""Pandera schema for UniProt ID Mapping entity.

Aligned with RULES.md v5.24 and UniProt ID Mapping API.
Source: https://www.uniprot.org/id-mapping/

Schema validates ChEMBL → UniProt ID mapping results:
- target_id: Source ChEMBL target ID
- uniprot_accession: Mapped UniProt accession (nullable for not_found)
- mapping_status: Status of mapping operation
"""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
MAPPING_STATUSES = ["found", "not_found", "error", "multiple"]
_SERIES_BOOL = "Series[bool]"


class IDMappingSchema(ETLRecordSchema):
    """UniProt ID Mapping validation schema for Silver layer.

    Validates mapping results from ChEMBL targets to UniProt accessions.
    Includes comprehensive UniProt entry metadata when mapping is found.
    """

    # === Primary Key ===
    target_id: Series[str] = pa.Field(
        nullable=False,
        description="Source ChEMBL target identifier (e.g., CHEMBL204)",
    )

    @pa.check("target_id", name="target_id_format")
    def _check_target_id(cls, series: Series[str]) -> Series[bool]:
        """Validate ChEMBL target ID format."""
        return cast(_SERIES_BOOL, series.str.match(r"^CHEMBL\d+$"))

    # === Mapping Result ===
    uniprot_accession: Series[str] | None = pa.Field(
        nullable=True,
        description="Mapped UniProt accession (e.g., P00742), None if not found",
    )

    @pa.check("uniprot_accession", name="uniprot_accession_format")
    def _check_uniprot_accession(cls, series: Series[str]) -> Series[bool]:
        """Validate UniProt accession format (6-10 alphanumeric chars)."""
        return cast(_SERIES_BOOL, series.isna() | series.str.match(r"^[A-Z0-9]{6,10}$"))

    mapping_status: Series[str] = pa.Field(
        nullable=False,
        description="Status of mapping: 'found', 'not_found', 'error', or 'multiple'",
    )

    @pa.check("mapping_status", name="mapping_status_values")
    def _check_mapping_status(cls, series: Series[str]) -> Series[bool]:
        """Validate mapping status is one of the allowed values."""
        return cast(_SERIES_BOOL, series.isin(MAPPING_STATUSES))

    # === UniProt Entry Metadata ===
    uniprot_entry_name: Series[str] | None = pa.Field(
        nullable=True,
        description="UniProt entry name (e.g., FA10_HUMAN)",
    )

    organism_scientific: Series[str] | None = pa.Field(
        nullable=True,
        description="Scientific organism name (e.g., Homo sapiens)",
    )

    organism_common: Series[str] | None = pa.Field(
        nullable=True,
        description="Common organism name (e.g., Human)",
    )

    taxonomy_id: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        ge=1,
        description="NCBI Taxonomy ID",
    )

    protein_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Recommended protein name",
    )

    gene_primary: Series[str] | None = pa.Field(
        nullable=True,
        description="Primary gene name",
    )

    sequence_length: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        ge=1,
        description="Protein sequence length",
    )

    sequence_mass: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        ge=1,
        description="Molecular weight in Daltons",
    )

    reviewed: Series[bool] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="True if Swiss-Prot (reviewed), False if TrEMBL",
    )

    annotation_score: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        ge=1,
        le=5,
        description="Quality score 1-5 (5 = best annotated)",
    )

    all_mappings: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of all accessions when multiple mappings found",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "IDMappingSchema"
        description = "UniProt ID Mapping Silver layer validation"


__all__ = [
    "MAPPING_STATUSES",
    "IDMappingSchema",
]
