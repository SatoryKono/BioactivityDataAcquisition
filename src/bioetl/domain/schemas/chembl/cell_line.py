"""Pandera schema for ChEMBL Cell Line entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
Source: ChEMBL REST API, table cell_dictionary.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CellLineSchema(ETLRecordSchema):
    """Cell Line validation schema for Silver layer.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).
    """

    # === Primary Key ===
    cell_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        unique=True,
        description="ChEMBL ID for cell line (PK).",
    )

    # === Core Metadata ===
    cell_name: Series[str] = pa.Field(
        nullable=False,
        description="Cell line name (e.g., HeLa, MCF7).",
    )
    cell_description: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell line description.",
    )

    # === Source Information ===
    cell_source_tissue: Series[str] | None = pa.Field(
        nullable=True,
        description="Source tissue (e.g., Cervix, Breast).",
    )
    cell_source_organism: Series[str] | None = pa.Field(
        nullable=True,
        description="Source organism (e.g., Homo sapiens).",
    )
    cell_source_tax_id: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="NCBI Taxonomy ID for source organism.",
    )

    # === Cell Type Classification ===
    cell_type: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell type classification (e.g., Cancer cell line).",
    )

    # === External Identifiers ===
    cellosaurus_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CVCL_[A-Z0-9]+$",
        description="Cellosaurus ID (external reference).",
    )
    clo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CLO_\d+$",
        description="Cell Line Ontology ID.",
    )
    cl_lincs_id: Series[str] | None = pa.Field(
        nullable=True,
        description="LINCS ID (Library of Integrated Network-Based Cellular Signatures).",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^EFO_\d+$",
        description="EFO ontology ID.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
