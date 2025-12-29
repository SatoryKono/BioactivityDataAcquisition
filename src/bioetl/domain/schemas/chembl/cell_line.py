"""Pandera schema for ChEMBL Cell Line entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
Source: ChEMBL REST API, table cell_dictionary.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CellLineSchema(ETLRecordSchema):
    """Cell line validation schema for Silver layer.

    Represents cell lines used in bioassays (e.g., HeLa, HEK293).
    """

    # === Primary Key ===
    cell_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
        description="Unique cell line identifier (PK)",
    )

    # === Core Fields ===
    cell_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Cell line name (e.g., HeLa, MCF-7)",
    )
    cell_description: Series[str] | None = pa.Field(
        nullable=True,
        description="Additional description of cell line",
    )

    # === Source Information ===
    cell_source_tissue: Series[str] | None = pa.Field(
        nullable=True,
        description="Tissue of origin (e.g., Cervix, Breast)",
    )
    cell_source_organism: Series[str] | None = pa.Field(
        nullable=True,
        description="Organism of origin (e.g., Homo sapiens)",
    )
    cell_source_tax_id: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="NCBI Taxonomy ID of source organism",
    )

    # === Ontology Cross-references ===
    clo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CLO:\d+$",
        description="Cell Line Ontology identifier",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^EFO:\d+$",
        description="Experimental Factor Ontology identifier",
    )
    cellosaurus_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CVCL_\w+$",
        description="Cellosaurus database identifier",
    )

    # === Status Flags ===
    downgraded: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="1 if cell line record is deprecated",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
