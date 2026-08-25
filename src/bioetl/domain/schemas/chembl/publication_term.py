"""Pandera schema for ChEMBL Publication Term entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
Renamed from DocumentTermSchema per ADR-024 (Entity Naming Unification).

PublicationTerms are derived entities extracted from Publication (ChEMBL Document)
    records by flattening the 1:M relationship between publications and their
    associated terms (MeSH headings, qualifiers, and keywords).
"""

from __future__ import annotations

from typing import ClassVar

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES

__all__ = [
    "PublicationTermSchema",
]


class PublicationTermSchema(ETLRecordSchema):
    """Publication Term validation schema for Silver layer.

    Composite Key: (publication_id, term_type, term)
    Entity ID is generated as SHA256 hash of the composite key.

    Term types:
    - MESH_HEADING: MeSH descriptor term
    - MESH_QUALIFIER: MeSH qualifier/subheading
    - KEYWORD: Author-provided keyword
    """

    # === Composite Key Fields ===
    publication_id: Series[str] = pa.Field(
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
        isin=sorted(PUBLICATION_TERM_TYPES),
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

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
        unique: ClassVar[list[str]] = ["publication_id", "term_type", "term"]
