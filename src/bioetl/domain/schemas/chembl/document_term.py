"""Pandera schema for ChEMBL Document Term entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.

DocumentTerms are derived entities extracted from Document records by
flattening the 1:M relationship between documents and their associated
terms (MeSH headings, keywords, concepts).
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentTermSchema(ETLRecordSchema):
    """Document Term validation schema for Silver layer.

    Composite Key: (document_chembl_id, term_type, term)
    Entity ID is generated as SHA256 hash of the composite key.

    Term types:
    - MESH_HEADING: MeSH descriptor term
    - MESH_QUALIFIER: MeSH qualifier/subheading
    - KEYWORD: Author-provided keyword
    - CONCEPT: ChEMBL-derived concept
    """

    # === Composite Key Fields ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="FK → Document ChEMBL ID.",
    )
    term: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Term text (e.g., 'Aspirin', 'kinase inhibitor').",
    )
    term_type: Series[str] = pa.Field(
        nullable=False,
        isin=["MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"],
        description="Term type classification.",
    )

    # === MeSH-specific Fields ===
    mesh_id: Series[str] | None = pa.Field(
        nullable=True,
        description="MeSH identifier (e.g., 'D001241').",
    )
    qualifier: Series[str] | None = pa.Field(
        nullable=True,
        description="MeSH qualifier (e.g., 'pharmacology').",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
