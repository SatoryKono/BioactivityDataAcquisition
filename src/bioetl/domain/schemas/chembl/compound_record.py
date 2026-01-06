"""Pandera schema for ChEMBL Compound Record entity.

Aligned with RULES.md v5.0 and ChEMBL 34 API schema.
Source: ChEMBL REST API /compound_record endpoint.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CompoundRecordSchema(ETLRecordSchema):
    """Compound Record validation schema for Silver layer.

    Compound records link molecules to documents. Contains the original
    compound name as it appears in the publication.

    Relationships:
    - M:1 → Molecule (molecule_chembl_id)
    - M:1 → Publication (document_chembl_id)
    - M:1 → Source (src_id)
    """

    # === Primary Key ===
    record_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
        description="ChEMBL record ID (PK).",
    )

    # === Foreign Keys ===
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="FK → Molecule.",
    )
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="FK → Publication.",
    )
    src_id: Series[int] = pa.Field(
        nullable=False,
        ge=1,
        description="FK → Source (data source).",
    )

    # === Source-specific Identifiers ===
    compound_key: Series[str] | None = pa.Field(
        nullable=True,
        description="Original compound key in source document.",
    )
    compound_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Original compound name in source document.",
    )
    src_compound_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Compound ID in original data source.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
