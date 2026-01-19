"""Pandera schema for ChEMBL Publication entity.

Aligned with RULES.md v5.10 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "ChemblPublicationSchema"]


class ChemblPublicationSchema(PublicationBaseSchema):
    """ChEMBL Publication validation schema for Silver layer."""

    # === Lookup metadata (ChEMBL-specific) ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: direct for ChEMBL ID lookup",
    )
    original_id: Series[str] = pa.Field(
        alias="_original_id",
        nullable=True,
        description="Original identifier used for lookup (document_chembl_id)",
    )

    # === Provider-specific Primary Key ===
    document_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )

    # === Provider-specific Identifiers ===
    patent_id: Series[str] = pa.Field(nullable=True, description="Patent ID.")
    src_id: Series[int] = pa.Field(nullable=True, description="Source ID.")

    # === Provider-specific Fields ===
    authors: Series[str] = pa.Field(nullable=True, description="Authors.")
    journal: Series[str] = pa.Field(nullable=True, description="Journal.")
    journal_full_title: Series[str] = pa.Field(
        nullable=True, description="Full journal title."
    )
    volume: Series[str] = pa.Field(nullable=True, description="Volume.")
    issue: Series[str] = pa.Field(nullable=True, description="Issue.")
    first_page: Series[str] = pa.Field(nullable=True, description="First page.")
    last_page: Series[str] = pa.Field(nullable=True, description="Last page.")

    # === Doc Type with ChEMBL-specific values ===
    doc_type: Series[str] = pa.Field(
        nullable=True,
        isin=["PUBLICATION", "PATENT", "DATASET", "BOOK"],
        description="Document type.",
    )

    # === DQ Fields ===
    _dq_warn: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ warning flag."
    )
    _dq_error: Series[bool] = pa.Field(
        nullable=True, default=False, description="DQ error flag."
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False
        coerce = True
