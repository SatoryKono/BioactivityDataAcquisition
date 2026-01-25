"""Pandera schema for UniProt ID Mapping entity.

Aligned with RULES.md v5.0 and UniProt ID Mapping API.
Source: https://www.uniprot.org/id-mapping/

Schema validates ChEMBL → UniProt ID mapping results:
- target_chembl_id: Source ChEMBL target ID
- uniprot_accession: Mapped UniProt accession (nullable for not_found)
- mapping_status: Status of mapping operation
"""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
MAPPING_STATUSES = ["found", "not_found", "error"]


class IDMappingSchema(ETLRecordSchema):
    """UniProt ID Mapping validation schema for Silver layer.

    Validates mapping results from ChEMBL targets to UniProt accessions.
    """

    # === Primary Key ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        description="Source ChEMBL target identifier (e.g., CHEMBL204)",
    )

    @pa.check("target_chembl_id", name="target_chembl_id_format")
    def _check_target_chembl_id(cls, series: Series[str]) -> Series[bool]:
        """Validate ChEMBL target ID format."""
        return cast("Series[bool]", series.str.match(r"^CHEMBL\d+$"))

    # === Mapping Result ===
    uniprot_accession: Series[str] | None = pa.Field(
        nullable=True,
        description="Mapped UniProt accession (e.g., P00742), None if not found",
    )

    @pa.check("uniprot_accession", name="uniprot_accession_format")
    def _check_uniprot_accession(cls, series: Series[str]) -> Series[bool]:
        """Validate UniProt accession format (6-10 alphanumeric chars)."""
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^[A-Z0-9]{6,10}$")
        )

    mapping_status: Series[str] = pa.Field(
        nullable=False,
        description="Status of mapping: 'found', 'not_found', or 'error'",
    )

    @pa.check("mapping_status", name="mapping_status_values")
    def _check_mapping_status(cls, series: Series[str]) -> Series[bool]:
        """Validate mapping status is one of the allowed values."""
        return cast("Series[bool]", series.isin(MAPPING_STATUSES))

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
